import json
import os
import requests

from odoo import api, models, _
from odoo.exceptions import UserError


class PayrollChatService(models.AbstractModel):
    _name = "chatbot_luong_groq.service"
    _description = "Payroll Chatbot Service (Groq)"

    def _get_rules_md(self):
        # data/salary_rules.md nằm cùng module
        module_dir = os.path.dirname(os.path.dirname(__file__))
        md_path = os.path.join(module_dir, "data", "salary_rules.md")
        try:
            with open(md_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            raise UserError(_("Không đọc được file salary_rules.md: %s") % str(e))

    def _get_groq_config(self):
        ICP = self.env["ir.config_parameter"].sudo()
        api_key = ICP.get_param("chatbot_luong_groq.groq_api_key") or ""
        model = ICP.get_param("chatbot_luong_groq.groq_model") or "llama-3.1-8b-instant"
        if not api_key:
            raise UserError(_("Bạn chưa cấu hình Groq API Key trong Settings."))
        return api_key, model

    def _call_groq(self, messages, temperature=0):
        api_key, model = self._get_groq_config()

        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }

        resp = requests.post(url, headers=headers, data=json.dumps(payload), timeout=60)
        if resp.status_code >= 400:
            raise UserError(_("Groq API lỗi (%s): %s") % (resp.status_code, resp.text))

        data = resp.json()
        return (data.get("choices") or [{}])[0].get("message", {}).get("content", "")

    def _compute(self, basic_salary, days_worked, late_hours, penalty_per_hour, allowances):
        # allowances: list[float]
        daily = basic_salary / 26.0
        total_salary = daily * days_worked
        total_allow = sum(allowances or [])
        late_penalty = late_hours * penalty_per_hour
        net = total_salary + total_allow - late_penalty

        return {
            "daily_salary": daily,
            "total_salary": total_salary,
            "total_allowance": total_allow,
            "late_penalty": late_penalty,
            "net_salary": net,
        }

    def _strip_markdown(self, text):
        """Loại bỏ các ký tự markdown cơ bản để tránh ** hoặc ### xuất hiện."""
        if not text:
            return text
        cleaned = text.replace("**", "")
        cleaned = cleaned.replace("__", "")
        cleaned = cleaned.replace("`", "")
        cleaned = cleaned.replace("###", "")
        cleaned = cleaned.replace("##", "")
        cleaned = cleaned.replace("#", "")
        return cleaned

    def chat(self, user_text):
        rules = self._get_rules_md()

        # Kiểm tra xem câu hỏi liên quan tới lương/nội quy hay không
        is_salary_related = self._is_salary_question(user_text)

        if is_salary_related:
            # 1) Dùng LLM để trích số liệu từ câu user (JSON)
            system = (
                "Bạn là trợ lý trích xuất dữ liệu. "
                "CHỈ TRẢ VỀ JSON THUẦN TÚY, KHÔNG THÊM BẤT KỲ TEXT NÀO KHÁC.\n\n"
                "Schema JSON cần trả về:\n"
                "{"
                "\"basic_salary\": number, "
                "\"days_worked\": number, "
                "\"late_hours\": number, "
                "\"penalty_per_hour\": number, "
                "\"allowances\": [{\"name\": string, \"amount\": number}]"
                "}\n\n"
                "Quy tắc (để hiểu ngữ cảnh):\n"
                f"{rules}\n\n"
                "Nếu thiếu dữ liệu nào thì điền 0. "
                "CHỈ trả về JSON object, KHÔNG giải thích, KHÔNG dùng markdown code block."
            )

            content = self._call_groq([
                {"role": "system", "content": system},
                {"role": "user", "content": user_text},
            ], temperature=0)

            # Extract JSON từ markdown block nếu có
            content = content.strip()
            if content.startswith("```json"):
                content = content.replace("```json", "").replace("```", "").strip()
            elif content.startswith("```"):
                content = content.replace("```", "").strip()

            try:
                parsed = json.loads(content)
            except Exception:
                raise UserError(_("Chatbot trả về không phải JSON hợp lệ. Nội dung: %s") % content)

            basic_salary = float(parsed.get("basic_salary") or 0)
            days_worked = float(parsed.get("days_worked") or 0)
            late_hours = float(parsed.get("late_hours") or 0)
            penalty_per_hour = float(parsed.get("penalty_per_hour") or 0)
            allowances = parsed.get("allowances") or []
            allowance_amounts = []
            for a in allowances:
                try:
                    allowance_amounts.append(float(a.get("amount") or 0))
                except Exception:
                    allowance_amounts.append(0.0)

            result = self._compute(basic_salary, days_worked, late_hours, penalty_per_hour, allowance_amounts)

            # 2) Nhờ LLM viết giải thích + trình bày đẹp (nhưng số liệu lấy từ Python)
            explain_system = (
                "Bạn là trợ lý tính lương và nội quy công ty. "
                "Hãy giải thích ngắn gọn từng bước theo RULES và trình bày kết quả rõ ràng. "
                "KHÔNG dùng markdown, KHÔNG dùng **, #, hoặc ký tự đặc biệt khác. Chỉ dùng text thuần.\n\n"
                "RULES:\n" + rules
            )

            explain_user = {
                "input": {
                    "basic_salary": basic_salary,
                    "days_worked": days_worked,
                    "late_hours": late_hours,
                    "penalty_per_hour": penalty_per_hour,
                    "allowances": allowances,
                },
                "computed": result,
            }

            explain = self._call_groq([
                {"role": "system", "content": explain_system},
                {"role": "user", "content": "Dữ liệu đã trích và tính bằng hệ thống:\n" + json.dumps(explain_user, ensure_ascii=False)},
            ], temperature=0.2)

            return {
                "parsed": parsed,
                "computed": result,
                "answer": self._strip_markdown(explain),
            }
        else:
            # Trả lời câu hỏi tổng quát
            system = (
                "Bạn là trợ lý hữu ích của công ty. Bạn có thể trả lời các câu hỏi về lương, nội quy, cũng như "
                "các câu hỏi tổng quát khác.\n\n"
                "QUAN TRỌNG: KHÔNG dùng markdown, KHÔNG dùng **, #, hoặc ký tự đặc biệt. Chỉ dùng text thuần.\n\n"
                "Thông tin về công ty:\n" + rules + "\n\n"
                "Hãy trả lời một cách thân thiện, chuyên nghiệp và rõ ràng."
            )

            answer = self._call_groq([
                {"role": "system", "content": system},
                {"role": "user", "content": user_text},
            ], temperature=0.7)

            return {
                "parsed": None,
                "computed": None,
                "answer": self._strip_markdown(answer),
            }

    def _is_salary_question(self, text):
        """Kiểm tra xem câu hỏi liên quan tới TÍNH TOÁN lương hay không (không phải chỉ hỏi về quy định)"""
        # Keywords liên quan tới tính toán lương
        salary_keywords = [
            "tính", "tính lương", "bao nhiêu", "mấy tiền", 
            "thực lãnh", "tổng lương", "phạt bao nhiêu",
            "công thức", "tính như thế nào"
        ]
        
        # Keywords liên quan tới thông tin (chỉ là câu hỏi thông tin)
        info_keywords = [
            "là gì", "là cái gì", "nào", "khi nào", "như thế nào là",
            "quy định", "nội quy", "điều khoản", "chế độ", 
            "bao gồm", "gồm những gì", "có những gì"
        ]
        
        text_lower = text.lower()
        
        # Nếu có keywords về thông tin, không phải là câu hỏi tính toán
        if any(kw in text_lower for kw in info_keywords):
            return False
        
        # Nếu có keywords về tính toán, thì là câu hỏi tính toán
        if any(kw in text_lower for kw in salary_keywords):
            return True
        
        return False
