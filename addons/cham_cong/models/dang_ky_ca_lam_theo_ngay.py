from odoo import models, fields, api
from odoo.exceptions import ValidationError

class DangKyCaLamTheoNgay(models.Model):
    _name = 'dang_ky_ca_lam_theo_ngay'
    _description = "Đăng ký ca làm theo ngày"
    _rec_name = 'ma_dot_ngay'

    _order = 'dot_dang_ky_id desc, ngay_lam asc'

    ma_dot_ngay = fields.Char("Mã đợt ngày", compute='_compute_ma_dot_ngay', store=True, readonly=True)
    dot_dang_ky_id = fields.Many2one('dot_dang_ky', string="Đợt đăng ký", required=True)
    nhan_vien_id = fields.Many2one('nhan_vien', string="Nhân viên", required=True)
    ngay_lam = fields.Date(string="Ngày làm", required=True)
    ca_lam = fields.Selection([
        ("", ""),
        ("Sáng", "Sáng"),
        ("Chiều", "Chiều"),
        ("Cả ngày", "Cả Ngày"),
    ], string="Ca làm", default="")

    @api.depends('dot_dang_ky_id', 'ngay_lam', 'nhan_vien_id')
    def _compute_ma_dot_ngay(self):
        for record in self:
            if record.dot_dang_ky_id and record.ngay_lam and record.nhan_vien_id:
                # Tạo mã: DDT + mã đợt + ngày + mã nhân viên
                # Ví dụ: DD001_20250124_TNDuyen001
                ma_dot = record.dot_dang_ky_id.ma_dot or 'XXX'
                ngay_format = record.ngay_lam.strftime('%Y%m%d')
                ma_nv = record.nhan_vien_id.ma_dinh_danh or record.nhan_vien_id.ho_va_ten
                record.ma_dot_ngay = f"{ma_dot}_{ngay_format}_{ma_nv}"
            else:
                record.ma_dot_ngay = ''

    @api.constrains('ngay_lam', 'dot_dang_ky_id')
    def _check_ngay_lam(self):
        for record in self:
            if record.ngay_lam and record.dot_dang_ky_id:
                if record.ngay_lam < record.dot_dang_ky_id.ngay_bat_dau or record.ngay_lam > record.dot_dang_ky_id.ngay_ket_thuc:
                    raise ValidationError(f'Ngày làm phải nằm trong khoảng thời gian của đợt đăng ký (từ {record.dot_dang_ky_id.ngay_bat_dau} đến {record.dot_dang_ky_id.ngay_ket_thuc})')
