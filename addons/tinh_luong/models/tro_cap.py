# -*- coding: utf-8 -*-
from odoo import fields, models

class TroCap(models.Model):
    _name = "tinh_luong.tro_cap"
    _description = "Trợ cấp"
    _order = "id desc"

    bang_luong_id = fields.Many2one("tinh_luong.bang_luong", string="Bảng lương", ondelete="cascade")
    name = fields.Char(string="Tên trợ cấp", required=True)
    loai = fields.Selection([
        ("an_trua", "Ăn trưa"),
        ("xang_xe", "Xăng xe"),
        ("dien_thoai", "Điện thoại"),
        ("khac", "Khác"),
    ], string="Loại", default="khac", required=True)

    so_tien = fields.Float(string="Số tiền", required=True, default=0.0)
    ghi_chu = fields.Text(string="Ghi chú")
