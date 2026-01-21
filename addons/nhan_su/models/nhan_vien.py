from odoo import models, fields

class NhanVien(models.Model):
    _name = "nhan_vien"
    _description = "Nhan vien"
    _rec_name = "ho_ten"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    ma_dinh_danh = fields.Char(string="Mã định danh", required=True, tracking=True)
    ho_ten = fields.Char(string="Họ tên", required=True, tracking=True)
    ngay_sinh = fields.Date(string="Ngày sinh", tracking=True)
    email = fields.Char(string="Email", tracking=True)
    so_dien_thoai = fields.Char(string="Số điện thoại", tracking=True)
    luong = fields.Float(string="Lương đơn giá", tracking=True, help="Đơn giá tính theo công/ngày")
    chuc_vu_id = fields.Many2one("chuc_vu", string="Chức vụ", tracking=True)
    phong_ban_ids = fields.Many2many("phong_ban", string="Phòng ban", tracking=True)

    

    # Bảo hiểm
    bhxh_ty_le = fields.Float(string="Tỷ lệ BHXH (%)", default=8.0, help="Tỷ lệ đóng BHXH (nhân viên)")
    bhyt_ty_le = fields.Float(string="Tỷ lệ BHYT (%)", default=1.5, help="Tỷ lệ đóng BHYT (nhân viên)")
    bhtn_ty_le = fields.Float(string="Tỷ lệ BHTN (%)", default=1.0, help="Tỷ lệ đóng BHTN (nhân viên)")

    _sql_constraints = [
        ("ma_dinh_danh_unique", "unique(ma_dinh_danh)", "Mã định danh đã tồn tại!"),
    ]
