from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import date


class BangLuong(models.Model):
    _name = "bang_luong"
    _description = "Bang luong"
    _rec_name = "name"
    _order = "nam desc, thang desc, id desc"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(compute="_compute_name", store=True, readonly=True)
    thang = fields.Integer(required=True, tracking=True, index=True)
    nam = fields.Integer(required=True, tracking=True, index=True)

    state = fields.Selection([
        ("draft", "Nháp"),
        ("confirmed", "Đã xác nhận"),
        ("approved", "Đã duyệt"),
        ("paid", "Đã chi"),
    ], default="draft", string="Trạng thái", tracking=True)

    line_ids = fields.One2many("bang_luong_line", "bang_luong_id", string="Chi tiết")

    tong_gross = fields.Float(compute="_compute_totals", store=True, readonly=True)
    tong_net = fields.Float(compute="_compute_totals", store=True, readonly=True)
    tong_bao_hiem = fields.Float(compute="_compute_totals", store=True, readonly=True)

    ghi_chu = fields.Text(string="Ghi chú")

    # ================= COMPUTE =================
    @api.depends("thang", "nam")
    def _compute_name(self):
        for r in self:
            r.name = f"Bảng lương {r.thang:02d}/{r.nam}" if r.thang and r.nam else "Bảng lương"

    @api.depends("line_ids.gross", "line_ids.net", "line_ids.tong_bao_hiem")
    def _compute_totals(self):
        for r in self:
            r.tong_gross = sum(r.line_ids.mapped("gross"))
            r.tong_net = sum(r.line_ids.mapped("net"))
            r.tong_bao_hiem = sum(r.line_ids.mapped("tong_bao_hiem"))

    @api.constrains("thang", "nam")
    def _check_unique_period(self):
        """Không cho tạo 2 bảng lương cùng tháng/năm"""
        for r in self:
            existing = self.search_count([
                ("thang", "=", r.thang),
                ("nam", "=", r.nam),
                ("id", "!=", r.id),
            ])
            if existing > 0:
                raise ValidationError(f"Bảng lương tháng {r.thang}/{r.nam} đã tồn tại!")

    @api.constrains("thang")
    def _check_thang(self):
        for r in self:
            if r.thang < 1 or r.thang > 12:
                raise ValidationError("Tháng phải nằm trong 1..12")

    # ================= ACTIONS =================
    def action_generate(self):
        """Sinh bảng lương từ tính công"""
        for sheet in self:
            if sheet.state != "draft":
                raise ValidationError("Chỉ sinh khi bảng lương ở trạng thái Nháp.")
            
            # Xóa chi tiết cũ
            sheet.line_ids.unlink()

            # Tìm tính công theo tháng/năm
            tinh_cong = self.env["tinh_cong"].search([
                ("thang", "=", sheet.thang),
                ("nam", "=", sheet.nam),
                ("state", "in", ["calculated", "confirmed", "locked"]),
            ], limit=1)

            if not tinh_cong or not tinh_cong.line_ids:
                raise ValidationError(f"Chưa tính công cho tháng {sheet.thang}/{sheet.nam}!")

            lines = []
            for tc_line in tinh_cong.line_ids:
                nv = tc_line.nhan_vien_id
                so_cong = tc_line.so_cong
                ot_gio = tc_line.ot_gio

                luong_don_gia = nv.luong or 0.0
                he_so = nv.chuc_vu_id.he_so if nv.chuc_vu_id else 1.0

                lines.append((0, 0, {
                    "nhan_vien_id": nv.id,
                    "so_cong": so_cong,
                    "ot_gio": ot_gio,
                    "luong_don_gia": luong_don_gia,
                    "he_so_chuc_vu": he_so,
                    "phu_cap": 0.0,
                    "thuong": 0.0,
                    "khau_tru_khac": 0.0,
                }))

            sheet.write({"line_ids": lines})
        
        return True

    def action_confirm(self):
        """Xác nhận bảng lương"""
        for r in self:
            if r.state != "draft":
                raise ValidationError("Chỉ xác nhận khi ở trạng thái Nháp!")
            r.write({"state": "confirmed"})

    def action_approve(self):
        """Duyệt bảng lương"""
        for r in self:
            if r.state != "confirmed":
                raise ValidationError("Chỉ duyệt khi ở trạng thái Đã xác nhận!")
            r.write({"state": "approved"})

    def action_paid(self):
        """Đánh dấu đã chi lương"""
        for r in self:
            if r.state not in ["approved", "draft"]:
                raise ValidationError("Chỉ chi lương khi ở trạng thái Đã duyệt!")
            r.write({"state": "paid"})
    
    def action_create_payment(self):
        """Tạo thanh toán từ bảng lương"""
        for sheet in self:
            if sheet.state not in ["approved"]:
                raise ValidationError("Chỉ thanh toán khi bảng lương đã được duyệt!")
            
            # Kiểm tra thanh toán đã tồn tại chưa
            existing_payment = self.env["thanh_toan_luong"].search([
                ("bang_luong_id", "=", sheet.id),
            ])
            if existing_payment:
                return {
                    "type": "ir.actions.act_window",
                    "name": "Thanh toán lương",
                    "res_model": "thanh_toan_luong",
                    "view_mode": "form",
                    "res_id": existing_payment[0].id,
                    "target": "current",
                }
            
            # Tạo thanh toán mới
            payment = self.env["thanh_toan_luong"].create({
                "bang_luong_id": sheet.id,
                "ma_thanh_toan": f"TT_{sheet.name}",
                "ngay_thanh_toan": date.today(),
            })
            
            # Tạo chi tiết thanh toán
            for line in sheet.line_ids:
                self.env["thanh_toan_luong_line"].create({
                    "thanh_toan_id": payment.id,
                    "bang_luong_line_id": line.id,
                    "so_tien_thanh_toan": line.net,
                })
            
            return {
                "type": "ir.actions.act_window",
                "name": "Thanh toán lương",
                "res_model": "thanh_toan_luong",
                "view_mode": "form",
                "res_id": payment.id,
                "target": "current",
            }

    def action_ai_check(self):
        """Kiểm tra bất thường bằng AI Rule"""
        for sheet in self:
            rule = self.env["ai_rule"].search([], limit=1)
            if not rule:
                raise ValidationError("Chưa cấu hình AI Rule.")

            for line in sheet.line_ids:
                flag = "normal"
                notes = []

                if line.so_cong > rule.max_cong:
                    flag = "warning"
                    notes.append(f"Công ({line.so_cong}) > {rule.max_cong}")

                if line.ot_gio > rule.max_ot_gio:
                    flag = "warning"
                    notes.append(f"OT ({line.ot_gio}h) > {rule.max_ot_gio}h")

                if line.net > rule.max_net:
                    flag = "danger"
                    notes.append(f"NET ({line.net}) > {rule.max_net}")

                line.write({
                    "ai_flag": flag,
                    "ai_note": "; ".join(notes) if notes else "Không phát hiện bất thường",
                })
        return True


class BangLuongLine(models.Model):
    _name = "bang_luong_line"
    _description = "Chi tiết bảng lương"

    bang_luong_id = fields.Many2one("bang_luong", required=True, ondelete="cascade", readonly=True)
    nhan_vien_id = fields.Many2one("nhan_vien", required=True, readonly=True)

    # Input từ tính công
    so_cong = fields.Float(default=0.0, string="Số công", readonly=True)
    ot_gio = fields.Float(default=0.0, string="Giờ OT", readonly=True)

    luong_don_gia = fields.Float(default=0.0, string="Lương đơn giá", readonly=True)
    he_so_chuc_vu = fields.Float(default=1.0, string="Hệ số chức vụ", readonly=True)

    # Các thành phần lương (editable)
    phu_cap = fields.Float(default=0.0, string="Phụ cấp")
    thuong = fields.Float(default=0.0, string="Thưởng")
    khau_tru_khac = fields.Float(default=0.0, string="Khấu trừ khác")
    
    # Tính toán tự động (readonly)
    luong_co_ban = fields.Float(compute="_compute_luong_co_ban", store=True, string="Lương cơ bản", readonly=True)
    ot_tien = fields.Float(compute="_compute_ot_tien", store=True, string="Tiền OT", readonly=True)
    
    # Lương trước bảo hiểm
    gross_base = fields.Float(compute="_compute_gross_base", store=True, string="Tổng cộng trước BH", readonly=True)

    # Bảo hiểm (tính dựa trên tỷ lệ từ nhân viên)
    bhxh = fields.Float(compute="_compute_bao_hiem", store=True, string="BHXH", readonly=True)
    bhyt = fields.Float(compute="_compute_bao_hiem", store=True, string="BHYT", readonly=True)
    bhtn = fields.Float(compute="_compute_bao_hiem", store=True, string="BHTN", readonly=True)
    tong_bao_hiem = fields.Float(compute="_compute_bao_hiem", store=True, string="Tổng BH", readonly=True)
    
    # Lương gross và net
    gross = fields.Float(compute="_compute_salary", store=True, string="Gross", readonly=True)
    net = fields.Float(compute="_compute_salary", store=True, string="Net (thực lĩnh)", readonly=True)

    # AI Flag
    ai_flag = fields.Selection([
        ("normal", "Bình thường"),
        ("warning", "Cảnh báo"),
        ("danger", "Nguy hiểm"),
    ], default="normal", readonly=True)
    ai_note = fields.Char(readonly=True, string="Ghi chú kiểm tra")

    # ==================== COMPUTE METHODS ====================
    
    @api.depends("so_cong", "luong_don_gia", "he_so_chuc_vu")
    def _compute_luong_co_ban(self):
        """Lương cơ bản = số công × lương đơn giá × hệ số chức vụ"""
        for r in self:
            r.luong_co_ban = (r.so_cong or 0.0) * (r.luong_don_gia or 0.0) * (r.he_so_chuc_vu or 1.0)

    @api.depends("ot_gio", "luong_don_gia")
    def _compute_ot_tien(self):
        """Tiền OT = giờ OT × (lương đơn giá / 8) × hệ số OT (1.5)"""
        for r in self:
            if r.luong_don_gia and r.ot_gio:
                r.ot_tien = r.ot_gio * (r.luong_don_gia / 8.0) * 1.5
            else:
                r.ot_tien = 0.0

    @api.depends("luong_co_ban", "ot_tien", "phu_cap", "thuong")
    def _compute_gross_base(self):
        """Tổng cộng trước BH = lương cơ bản + tiền OT + phụ cấp + thưởng"""
        for r in self:
            r.gross_base = (r.luong_co_ban or 0.0) + (r.ot_tien or 0.0) + (r.phu_cap or 0.0) + (r.thuong or 0.0)

    @api.depends(
        "nhan_vien_id", "gross_base",
        "nhan_vien_id.bhxh_ty_le", "nhan_vien_id.bhyt_ty_le", "nhan_vien_id.bhtn_ty_le"
    )
    def _compute_bao_hiem(self):
        """Tính bảo hiểm theo tỷ lệ từ nhân viên"""
        for r in self:
            base = r.gross_base or 0.0
            if r.nhan_vien_id:
                r.bhxh = base * (r.nhan_vien_id.bhxh_ty_le or 0.0) / 100.0
                r.bhyt = base * (r.nhan_vien_id.bhyt_ty_le or 0.0) / 100.0
                r.bhtn = base * (r.nhan_vien_id.bhtn_ty_le or 0.0) / 100.0
                r.tong_bao_hiem = r.bhxh + r.bhyt + r.bhtn
            else:
                r.bhxh = r.bhyt = r.bhtn = r.tong_bao_hiem = 0.0

    @api.depends("gross_base", "tong_bao_hiem", "khau_tru_khac")
    def _compute_salary(self):
        """
        Gross = gross_base (tổng cộng trước BH)
        Net = gross_base - bảo hiểm - khấu trừ khác
        """
        for r in self:
            r.gross = r.gross_base or 0.0
            r.net = (r.gross_base or 0.0) - (r.tong_bao_hiem or 0.0) - (r.khau_tru_khac or 0.0)
            r.net = max(0, r.net)  # Không được âm




