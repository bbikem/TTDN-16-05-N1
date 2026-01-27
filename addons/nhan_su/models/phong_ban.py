from odoo import models, fields, api

class PhongBan(models.Model):
    _name = 'phong_ban'
    _description = 'Bảng chứa thông tin phòng ban'
    _rec_name = 'ten_phong_ban'

    ma_phong_ban = fields.Char("Mã phòng ban", compute="_compute_ma_phong_ban", store=True, readonly=True)
    ten_phong_ban = fields.Char("Tên phòng ban", required=True)
    ma_phong_ban_preview = fields.Char("Mã phòng ban", compute="_compute_ma_phong_ban_preview", store=False, readonly=True)
    so_nhan_vien = fields.Integer("Số nhân viên", compute="_compute_so_nhan_vien", store=False)
    
    @api.depends('ten_phong_ban')
    def _compute_ma_phong_ban(self):
        for record in self:
            if record.id and record.ten_phong_ban:
                # Extract chữ cái đầu của mỗi từ
                words = record.ten_phong_ban.strip().split()
                initials = ''.join([word[0].upper() for word in words if word])
                
                # Đếm tất cả record có ID <= record.id (thứ tự tạo)
                count = self.search_count([('id', '<=', record.id)])
                
                # Sinh mã: PB + initials + số thứ tự
                record.ma_phong_ban = f'PB{initials}{count:03d}'
            else:
                record.ma_phong_ban = ''
    
    @api.depends('ten_phong_ban')
    def _compute_ma_phong_ban_preview(self):
        for record in self:
            if record.ten_phong_ban:
                # Extract chữ cái đầu của mỗi từ
                words = record.ten_phong_ban.strip().split()
                initials = ''.join([word[0].upper() for word in words if word])
                
                # Tính thứ tự dựa trên số record hiện có
                if record.id:
                    count = self.search_count([('id', '<=', record.id)])
                else:
                    # Cho form mới, đếm tất cả record hiện có + 1
                    count = self.search_count([]) + 1
                
                record.ma_phong_ban_preview = f'PB{initials}{count:03d}'
            else:
                record.ma_phong_ban_preview = ''
    
    def _compute_so_nhan_vien(self):
        for record in self:
            record.so_nhan_vien = self.env['nhan_vien'].search_count([('phong_ban_id', '=', record.id)])
    