# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class KhauTruLuong(models.Model):
    """Model quản lý hạng mục khấu trừ lương"""
    _name = 'khau_tru_luong'
    _description = "Khấu trừ lương"
    _rec_name = 'ten_khau_tru'
    _order = 'thu_tu'

    ten_khau_tru = fields.Char(string="Tên hạng mục khấu trừ", required=True)
    loai = fields.Selection([
        ('bhxh', 'BHXH'),
        ('bhyt', 'BHYT'),
        ('bhtn', 'BHTN'),
        ('thue_tncn', 'Thuế TNCN'),
        ('khac', 'Khác'),
    ], string="Loại khấu trừ", default='khac', required=True)

    # Tính toán
    kiểu_tinh = fields.Selection([
        ('fixed', 'Cố định'),
        ('percent', 'Phần trăm'),
    ], string="Kiểu tính", default='percent')
    
    gia_tri = fields.Float(string="Giá trị", default=0.0)
    
    # Cấu hình
    du_dieu_kien = fields.Text(string="Điều kiện áp dụng",
                               help="VD: so_cong >= 20 and phong_ban == 'IT'")
    thu_tu = fields.Integer(string="Thứ tự", default=10, help="Thứ tự tính toán")
    active = fields.Boolean(string="Có hiệu lực", default=True)
    
    ghi_chu = fields.Text(string="Ghi chú")
    
    @api.constrains('gia_tri')
    def _check_gia_tri(self):
        for r in self:
            if r.gia_tri < 0:
                raise ValidationError("Giá trị khấu trừ không được âm!")


class ThanhToanLuong(models.Model):
    """Model quản lý thanh toán lương"""
    _name = 'thanh_toan_luong'
    _description = "Thanh toán lương"
    _rec_name = 'ma_thanh_toan'
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = 'ngay_thanh_toan desc'

    # Thông tin cơ bản
    ma_thanh_toan = fields.Char(string="Mã thanh toán", tracking=True, 
                                readonly=True, index=True, copy=False)
    bang_luong_id = fields.Many2one('bang_luong', string="Bảng lương", required=True, 
                                    ondelete='cascade', tracking=True)
    
    ngay_thanh_toan = fields.Date(string="Ngày thanh toán", required=True, tracking=True, 
                                 default=lambda self: fields.Date.today())
    kinh_te = fields.Selection([
        ('bank', 'Chuyển khoản'),
        ('cash', 'Tiền mặt'),
        ('other', 'Khác'),
    ], string="Kinh tế", default='bank', required=True, tracking=True)
    
    # Trạng thái
    state = fields.Selection([
        ('draft', 'Nháp'),
        ('confirmed', 'Đã xác nhận'),
        ('processed', 'Đã xử lý'),
        ('done', 'Hoàn thành'),
    ], default='draft', string="Trạng thái", tracking=True)
    
    # Chi tiết thanh toán
    line_ids = fields.One2many('thanh_toan_luong_line', 'thanh_toan_id', string="Chi tiết")
    
    # Thống kê
    tong_net = fields.Float(compute="_compute_totals", store=True, readonly=True)
    tong_thanh_toan = fields.Float(compute="_compute_totals", store=True, readonly=True)
    
    ghi_chu = fields.Text(string="Ghi chú")
    
    @api.model_create_multi
    def create(self, vals_list):
        """Auto-generate mã thanh toán"""
        from datetime import datetime
        for vals in vals_list:
            if not vals.get('ma_thanh_toan'):
                now = datetime.now()
                date_str = now.strftime('%Y%m%d')
                count = self.search_count([('ma_thanh_toan', 'like', f'TT{date_str}%')]) + 1
                vals['ma_thanh_toan'] = f'TT{date_str}{count:03d}'
            
            # Auto-populate line_ids nếu chưa có
            if vals.get('bang_luong_id') and not vals.get('line_ids'):
                bang_luong = self.env['bang_luong'].browse(vals['bang_luong_id'])
                lines = []
                for line in bang_luong.line_ids:
                    lines.append((0, 0, {
                        'bang_luong_line_id': line.id,
                        'so_tien_thanh_toan': line.net,
                    }))
                vals['line_ids'] = lines
        return super().create(vals_list)
    
    @api.onchange('bang_luong_id')
    def _onchange_bang_luong(self):
        """Tự động populate line_ids từ bảng lương được chọn"""
        if self.bang_luong_id:
            lines = []
            for line in self.bang_luong_id.line_ids:
                lines.append((0, 0, {
                    'bang_luong_line_id': line.id,
                    'so_tien_thanh_toan': line.net,  # Mặc định thanh toán full
                }))
            self.line_ids = lines
    
    @api.depends('line_ids.net', 'line_ids.so_tien_thanh_toan')
    def _compute_totals(self):
        for r in self:
            r.tong_net = sum(r.line_ids.mapped('net'))
            r.tong_thanh_toan = sum(r.line_ids.mapped('so_tien_thanh_toan'))
    
    def action_confirm(self):
        """Xác nhận thanh toán"""
        for r in self:
            if r.state != 'draft':
                raise ValidationError("Chỉ xác nhận khi ở trạng thái Nháp!")
            r.state = 'confirmed'
    
    def action_process(self):
        """Xử lý thanh toán"""
        for r in self:
            if r.state != 'confirmed':
                raise ValidationError("Chỉ xử lý khi ở trạng thái Đã xác nhận!")
            r.state = 'processed'
    
    def action_done(self):
        """Hoàn thành thanh toán"""
        for r in self:
            if r.state != 'processed':
                raise ValidationError("Chỉ hoàn thành khi ở trạng thái Đã xử lý!")
            r.state = 'done'


class ThanhToanLuongLine(models.Model):
    """Chi tiết thanh toán lương"""
    _name = 'thanh_toan_luong_line'
    _description = "Chi tiết thanh toán lương"
    _rec_name = 'nhan_vien_id'

    thanh_toan_id = fields.Many2one('thanh_toan_luong', required=True, ondelete='cascade')
    bang_luong_line_id = fields.Many2one('bang_luong_line', string="Dòng lương")
    
    nhan_vien_id = fields.Many2one('nhan_vien', string="Nhân viên", related='bang_luong_line_id.nhan_vien_id')
    net = fields.Float(string="Lương NET", related='bang_luong_line_id.net')
    
    # Thanh toán
    so_tien_thanh_toan = fields.Float(string="Số tiền thanh toán", default=0.0)
    so_tien_chuyen_lan_sau = fields.Float(string="Số tiền chuyển lần sau", compute="_compute_chuyen_lan_sau", store=True)
    
    # Thông tin thanh toán
    so_tai_khoan = fields.Char(string="Số tài khoản")
    ngan_hang = fields.Char(string="Ngân hàng")
    chu_tk = fields.Char(string="Chủ tài khoản")
    
    ghi_chu = fields.Text(string="Ghi chú")
    
    @api.depends('net', 'so_tien_thanh_toan')
    def _compute_chuyen_lan_sau(self):
        for r in self:
            r.so_tien_chuyen_lan_sau = max(0, r.net - r.so_tien_thanh_toan)
