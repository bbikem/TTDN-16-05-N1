from odoo import models, fields

class PhongBan(models.Model):
    _name = "phong_ban"
    _description = "Phòng ban"
    _rec_name = "ten_phong_ban"
    _inherit = ["mail.thread", "mail.activity.mixin"]  # ✅ bật chatter + activity

    ma_phong_ban = fields.Char(string="Mã phòng ban", required=True, tracking=True)
    ten_phong_ban = fields.Char(string="Tên phòng ban", required=True, tracking=True)
    mo_ta = fields.Text(string="Mô tả", tracking=True)

    _sql_constraints = [
        ("ma_phong_ban_unique", "unique(ma_phong_ban)", "Mã phòng ban đã tồn tại!"),
    ]
