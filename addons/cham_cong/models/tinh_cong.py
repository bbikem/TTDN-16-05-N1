# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import timedelta, datetime
from odoo.exceptions import ValidationError


class TinhCong(models.Model):
    """Model quản lý tính công của nhân viên"""
    _name = 'tinh_cong'
    _description = "Tính công"
    _rec_name = 'ma_tinh_cong'
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = 'ngay_bat_dau desc'

    # Thông tin cơ bản
    ma_tinh_cong = fields.Char(string="Mã tính công", required=True, tracking=True, copy=False,
                               readonly=True, index=True)
    ngay_bat_dau = fields.Date(string="Ngày bắt đầu", required=True, tracking=True)
    ngay_ket_thuc = fields.Date(string="Ngày kết thúc", required=True, tracking=True)
    thang = fields.Integer(string="Tháng", compute="_compute_thang_nam", store=True, tracking=True)
    nam = fields.Integer(string="Năm", compute="_compute_thang_nam", store=True, tracking=True)
    
    phong_ban_id = fields.Many2one('phong_ban', string="Phòng ban", tracking=True)
    nhan_vien_ids = fields.Many2many('nhan_vien', string="Nhân viên")
    
    # Trạng thái
    state = fields.Selection([
        ('draft', 'Nháp'),
        ('calculated', 'Đã tính toán'),
        ('confirmed', 'Đã xác nhận'),
        ('locked', 'Khóa'),
    ], default='draft', string="Trạng thái", tracking=True)
    
    # Chi tiết tính công
    line_ids = fields.One2many('tinh_cong_line', 'tinh_cong_id', string="Chi tiết tính công")
    
    # Thống kê
    tong_nhan_vien = fields.Integer(compute="_compute_stats", store=True)
    tong_cong = fields.Float(compute="_compute_stats", store=True)
    tong_ot = fields.Float(compute="_compute_stats", store=True)
    
    ghi_chu = fields.Text(string="Ghi chú")
    
    @api.model_create_multi
    def create(self, vals_list):
        """Auto-generate mã tính công"""
        for vals in vals_list:
            if not vals.get('ma_tinh_cong'):
                # Cố gắng lấy từ sequence
                try:
                    ma = self.env['ir.sequence'].next_by_code('tinh_cong.sequence')
                    if ma:
                        vals['ma_tinh_cong'] = ma
                except:
                    pass
                
                # Nếu không có sequence, tạo mã thủ công
                if not vals.get('ma_tinh_cong'):
                    now = datetime.now()
                    # Tạo mã: TC/YYYYMMDD/001
                    date_str = now.strftime('%Y%m%d')
                    count = self.search_count([('ma_tinh_cong', 'like', f'TC/{date_str}%')]) + 1
                    vals['ma_tinh_cong'] = f'TC/{date_str}/{count:03d}'
        
        return super().create(vals_list)
    
    @api.depends('ngay_bat_dau')
    def _compute_thang_nam(self):
        for r in self:
            if r.ngay_bat_dau:
                r.thang = r.ngay_bat_dau.month
                r.nam = r.ngay_bat_dau.year
            else:
                r.thang = r.nam = 0
    
    @api.depends('line_ids.so_cong', 'line_ids.ot_gio')
    def _compute_stats(self):
        for r in self:
            r.tong_nhan_vien = len(r.line_ids)
            r.tong_cong = sum(r.line_ids.mapped('so_cong'))
            r.tong_ot = sum(r.line_ids.mapped('ot_gio'))
    
    @api.constrains('ngay_bat_dau', 'ngay_ket_thuc')
    def _check_dates(self):
        for r in self:
            if r.ngay_bat_dau and r.ngay_ket_thuc:
                if r.ngay_bat_dau > r.ngay_ket_thuc:
                    raise ValidationError("Ngày bắt đầu không được sau ngày kết thúc!")
    
    def action_calculate(self):
        """Tính toán công từ bảng chấm công"""
        for record in self:
            if record.state != 'draft':
                raise ValidationError("Chỉ tính toán khi ở trạng thái Nháp!")
            
            record.line_ids.unlink()
            
            # Tìm tất cả bảng chấm công trong khoảng thời gian
            domain = [
                ('ngay_cham_cong', '>=', record.ngay_bat_dau),
                ('ngay_cham_cong', '<=', record.ngay_ket_thuc),
            ]
            
            if record.phong_ban_id:
                domain.append(('nhan_vien_id.phong_ban_ids', '=', record.phong_ban_id.id))
            
            if record.nhan_vien_ids:
                domain.append(('nhan_vien_id', 'in', record.nhan_vien_ids.ids))
            
            bang_cham_cong = self.env['bang_cham_cong'].search(domain)
            
            # Gom nhóm theo nhân viên
            by_nv = {}
            for cc in bang_cham_cong:
                nv_id = cc.nhan_vien_id.id
                if nv_id not in by_nv:
                    by_nv[nv_id] = {
                        'so_cong': 0.0,
                        'so_ot': 0.0,
                        'so_di_muon': 0.0,
                        'so_ve_som': 0.0,
                        'so_vang': 0.0,
                    }
                
                # Tính công (dùng computed field so_cong: 0/0.5/1.0 dựa trên trang_thai)
                by_nv[nv_id]['so_cong'] += cc.so_cong
                
                # Tính OT
                if cc.ot_gio:
                    by_nv[nv_id]['so_ot'] += cc.ot_gio
                
                # Đi muộn
                if cc.phut_di_muon > 0:
                    by_nv[nv_id]['so_di_muon'] += 1
                
                # Về sớm
                if cc.phut_ve_som > 0:
                    by_nv[nv_id]['so_ve_som'] += 1
                
                # Vắng mặt
                if cc.trang_thai == 'vang_mat':
                    by_nv[nv_id]['so_vang'] += 1
            
            # Tạo chi tiết
            lines = []
            for nv_id, stats in by_nv.items():
                lines.append((0, 0, {
                    'nhan_vien_id': nv_id,
                    'so_cong': stats['so_cong'],
                    'ot_gio': stats['so_ot'],
                    'so_di_muon': stats['so_di_muon'],
                    'so_ve_som': stats['so_ve_som'],
                    'so_vang': stats['so_vang'],
                }))
            
            record.write({
                'line_ids': lines,
                'state': 'calculated'
            })
        
        return True
    
    def action_confirm(self):
        """Xác nhận tính công"""
        for r in self:
            if r.state not in ['calculated']:
                raise ValidationError("Chỉ xác nhận khi ở trạng thái Đã tính toán!")
            r.state = 'confirmed'
    
    def action_lock(self):
        """Khóa tính công (không sửa được bảng chấm công)"""
        for r in self:
            if r.state != 'confirmed':
                raise ValidationError("Chỉ khóa khi ở trạng thái Đã xác nhận!")
            
            # Khóa tất cả bảng chấm công
            bang_cham_cong = self.env['bang_cham_cong'].search([
                ('ngay_cham_cong', '>=', r.ngay_bat_dau),
                ('ngay_cham_cong', '<=', r.ngay_ket_thuc),
            ])
            bang_cham_cong.write({'is_locked': True})
            
            r.state = 'locked'
    
    def action_unlock(self):
        """Mở khóa tính công"""
        for r in self:
            if r.state != 'locked':
                raise ValidationError("Chỉ mở khóa khi ở trạng thái Khóa!")
            
            # Mở khóa tất cả bảng chấm công
            bang_cham_cong = self.env['bang_cham_cong'].search([
                ('ngay_cham_cong', '>=', r.ngay_bat_dau),
                ('ngay_cham_cong', '<=', r.ngay_ket_thuc),
            ])
            bang_cham_cong.write({'is_locked': False})
            
            r.state = 'confirmed'


class TinhCongLine(models.Model):
    """Chi tiết tính công"""
    _name = 'tinh_cong_line'
    _description = "Chi tiết tính công"
    _rec_name = 'nhan_vien_id'
    
    tinh_cong_id = fields.Many2one('tinh_cong', required=True, ondelete='cascade')
    nhan_vien_id = fields.Many2one('nhan_vien', required=True)
    
    # Tính toán công
    so_cong = fields.Float(string="Số công", default=0.0)
    ot_gio = fields.Float(string="Giờ OT", default=0.0)
    
    # Thống kê lỗi
    so_di_muon = fields.Integer(string="Số lần đi muộn", default=0)
    so_ve_som = fields.Integer(string="Số lần về sớm", default=0)
    so_vang = fields.Integer(string="Số lần vắng mặt", default=0)
    
    # Ghi chú
    ghi_chu = fields.Text(string="Ghi chú")
