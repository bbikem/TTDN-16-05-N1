from odoo import models, fields

class ChungChi(models.Model):
    _name = "chung_chi"
    _description = "Chung chi"

    nhan_vien_id = fields.Many2one("nhan_vien", required=True, ondelete="cascade")
    ten_chung_chi = fields.Char(required=True)
    so_hieu = fields.Char()
    don_vi_cap = fields.Char()
    ngay_cap = fields.Date()
    ngay_het_han = fields.Date()
    ghi_chu = fields.Text()
