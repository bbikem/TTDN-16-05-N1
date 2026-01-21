from odoo import models, fields

class LichSuCongTac(models.Model):
    _name = "lich_su_cong_tac"
    _description = "Lich su cong tac"

    nhan_vien_id = fields.Many2one("nhan_vien", required=True, ondelete="cascade")
    phong_ban_id = fields.Many2one("phong_ban")
    chuc_vu_id = fields.Many2one("chuc_vu")
    tu_ngay = fields.Date(required=True)
    den_ngay = fields.Date()
    ghi_chu = fields.Text()
