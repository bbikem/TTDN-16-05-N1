from odoo import models, fields, api
from datetime import datetime, date, timedelta
import calendar

class DotDangKy(models.Model):
    _name = 'dot_dang_ky'
    _description = "Bảng chứa thông tin đợt đăng ký"
    _rec_name = 'ten_dot'

    ma_dot = fields.Char("Mã đợt", readonly=True, store=True)
    ma_dot_preview = fields.Char("Mã đợt", compute="_compute_ma_dot_preview", store=False, readonly=True)
    ten_dot = fields.Char("Tên đợt", compute='_compute_ten_dot', store=True)
    thang_dang_ky = fields.Selection(
        [(str(i), f'Tháng {i}') for i in range(1, 13)],
        string="Tháng đăng ký",
        required=True
    )
    ngay_bat_dau = fields.Date("Thời gian bắt đầu", compute='_compute_thoi_gian', store=True)
    ngay_ket_thuc = fields.Date("Thời gian kết thúc", compute='_compute_thoi_gian', store=True)
    han_dang_ky = fields.Date("Hạn đăng ký", required=True)
    trang_thai_dang_ky = fields.Selection(
        [
            ("Đang mở", "Đang mở"),
            ("Đã hết hạn", "Đã hết hạn"),
            ("Đã đóng", "Đã đóng")
        ],
        string="Trạng thái đăng ký",
        compute="_compute_trang_thai_dang_ky",
        store=True
    )
    trang_thai_ap_dung = fields.Selection(
        [
            ("Đang áp dụng", "Đang áp dụng"),
            ("Ngừng áp dụng", "Ngừng áp dụng"),
            ("Chưa áp dụng", "Chưa áp dụng")
        ],
        string="Trạng thái áp dụng",
        compute="_compute_trang_thai_ap_dung",
        store=True
    )
    dang_ky_ca_lam_theo_ngay_ids = fields.One2many('dang_ky_ca_lam_theo_ngay', inverse_name='dot_dang_ky_id', string="Đăng ký ca làm")

    @api.model
    def create(self, vals):
        record = super().create(vals)
        return record

    @api.depends('thang_dang_ky')
    def _compute_ma_dot_preview(self):
        for record in self:
            if not record.thang_dang_ky:
                record.ma_dot_preview = ''
            elif record.id and record.ma_dot:
                # Nếu đã có ID (record lưu rồi), lấy mã từ DB
                record.ma_dot_preview = record.ma_dot
            else:
                # Cho form mới, lấy số tiếp theo từ sequence
                sequence = self.env['ir.sequence'].search([('code', '=', 'dot_dang_ky.sequence')], limit=1)
                next_num = sequence.number_next if sequence else 1
                record.ma_dot_preview = f'DD{next_num:03d}'
            
    @api.depends('han_dang_ky')
    def _compute_trang_thai_dang_ky(self):
        today = date.today()
        for record in self:
            if record.han_dang_ky and today > record.han_dang_ky:
                record.trang_thai_dang_ky = "Đã hết hạn"
            else:
                record.trang_thai_dang_ky = "Đang mở"
    
    @api.depends('ngay_bat_dau', 'ngay_ket_thuc')
    def _compute_trang_thai_ap_dung(self):
        today = date.today()
        for record in self:
            if record.ngay_ket_thuc and today > record.ngay_ket_thuc:
                record.trang_thai_ap_dung = "Ngừng áp dụng"
            elif record.ngay_bat_dau and today > record.ngay_bat_dau:
                record.trang_thai_ap_dung = "Đang áp dụng"
            else:
                record.trang_thai_ap_dung = "Chưa áp dụng"
    
    @api.depends('thang_dang_ky')
    def _compute_thoi_gian(self):
        for record in self:
            if record.thang_dang_ky:
                thang = int(record.thang_dang_ky)
                nam = datetime.now().year
                ngay_dau_thang = date(nam, thang, 1)
                ngay_cuoi_thang = date(nam, thang, calendar.monthrange(nam, thang)[1])
                record.ngay_bat_dau = ngay_dau_thang
                record.ngay_ket_thuc = ngay_cuoi_thang
            else:
                record.ngay_bat_dau = False
                record.ngay_ket_thuc = False
    
    @api.depends('thang_dang_ky')
    def _compute_ten_dot(self):
        for record in self:
            if record.thang_dang_ky:
                nam = datetime.now().year
                record.ten_dot = f"Đợt làm việc Tháng {record.thang_dang_ky}/{nam}"
            else:
                record.ten_dot = False

    @api.model_create_multi
    def create(self, vals_list):
        sequence = self.env['ir.sequence'].search([('code', '=', 'dot_dang_ky.sequence')], limit=1)
        for vals in vals_list:
            if not vals.get('ma_dot'):
                # Lấy số tiếp theo và sinh mã
                next_num = sequence.number_next if sequence else 1
                vals['ma_dot'] = f'DD{next_num:03d}'
                # Tăng counter sequence cho record tiếp theo
                if sequence:
                    sequence.number_next = next_num + 1
        return super().create(vals_list)