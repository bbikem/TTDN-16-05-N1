from odoo import fields, models

class PayrollChatWizard(models.TransientModel):
    _name = "chatbot_luong_groq.wizard"
    _description = "Payroll Chatbot Wizard"

    user_text = fields.Text(string="Bạn nhập yêu cầu")
    answer = fields.Text(string="Kết quả")
    debug_json = fields.Text(string="Debug (JSON)", readonly=True)

    def action_chat(self):
        self.ensure_one()
        service = self.env["chatbot_luong_groq.service"]
        res = service.chat(self.user_text or "")
        self.answer = res.get("answer", "")
        # debug cho dev xem parsed + computed
        self.debug_json = str(res)
        return {
            "type": "ir.actions.act_window",
            "res_model": "chatbot_luong_groq.wizard",
            "view_mode": "form",
            "res_id": self.id,
            "target": "new",
        }
