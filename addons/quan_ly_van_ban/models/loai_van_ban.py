from odoo import models, fields


class LoaiVanBan(models.Model):
    _name = 'loai_van_ban'
    _description = 'Bảng chứa thông tin loại văn bản'
    _rec_name = 'ten_loai_van_ban'

    ma_loai_van_ban = fields.Char(string="Mã loại văn bản", required=True)
    ten_loai_van_ban = fields.Char(string="Tên loại văn bản", required=True)
    he_so = fields.Float(string="Hệ số", required=True, default=1.0)

    mo_ta = fields.Text(string="Mô tả")

    _sql_constraints = [
        ('ma_chuc_vu_unique', 'unique(ma_chuc_vu)', 'Mã chức vụ đã tồn tại!'),
    ]
