from odoo import models, fields, api
from datetime import datetime
from odoo.exceptions import ValidationError
import unicodedata

class NhanVien(models.Model):
    _name = 'nhan_vien'
    _description = 'Bảng chứa thông tin nhân viên'
    _rec_name = 'ho_va_ten'
    _order = 'ten asc, tuoi desc'

    ma_dinh_danh = fields.Char("Mã định danh", readonly=True, store=True)
    ma_dinh_danh_preview = fields.Char("Mã định danh", compute="_compute_ma_dinh_danh_preview", store=False, readonly=True)
    ho_ten_dem = fields.Char("Họ tên đệm", required=True)
    ten = fields.Char("Tên", required=True)
    ho_va_ten = fields.Char("Họ và tên", compute="_compute_ho_va_ten", store=True)
    ngay_sinh = fields.Date("Ngày sinh", required=True)
    tuoi = fields.Integer("Tuổi", compute="_compute_tinh_tuoi", store=True)
    gioi_tinh = fields.Selection(
        [
            ("Nam", "Nam"),
            ("Nữ", "Nữ")
        ],
        string="Giới tính",
        required=True,
    )
    que_quan = fields.Char("Quê quán", required=True)
    email = fields.Char("Email", required=True)
    so_dien_thoai = fields.Char("Số điện thoại", required=True)
    anh = fields.Binary("Ảnh")
    phong_ban_id = fields.Many2one("phong_ban", string="Phòng ban", required=True)
    chuc_vu_id = fields.Many2one("chuc_vu", string="Chức vụ", required=True)
    
    def _remove_accents(self, text):
        """Loại bỏ dấu từ text tiếng Việt"""
        if not text:
            return ''
        nfkd_form = unicodedata.normalize('NFKD', text)
        return ''.join([c for c in nfkd_form if not unicodedata.combining(c)])
    
    def _get_next_employee_code(self, ho_ten_dem, ten):
        """Tính mã nhân viên dựa trên họ tên đệm, tên và số thứ tự"""
        if not ho_ten_dem or not ten:
            return ''
        
        # Loại bỏ dấu
        ho_ten_dem_no_accent = self._remove_accents(ho_ten_dem)
        ten_no_accent = self._remove_accents(ten)
        
        # Lấy chữ cái đầu của từng từ trong họ tên đệm
        initials = ''.join([word[0].upper() for word in ho_ten_dem_no_accent.strip().split() if word])
        # Lấy tên (từ cuối) với chữ cái đầu hoa
        name_part = ten_no_accent.strip().capitalize() if ten_no_accent else ''
        
        # Lấy số thứ tự từ sequence
        sequence = self.env['ir.sequence'].search([('code', '=', 'nhan_vien.sequence')], limit=1)
        next_num = sequence.number_next if sequence else 1
        
        # Sinh mã: ví dụ TNDuyen001
        return f'{initials}{name_part}{next_num:03d}'
    
    @api.depends('ho_ten_dem', 'ten')
    def _compute_ma_dinh_danh_preview(self):
        for record in self:
            if record.ho_ten_dem and record.ten:
                # Nếu đã có ID (record lưu rồi), lấy mã từ DB
                if record.id and record.ma_dinh_danh:
                    record.ma_dinh_danh_preview = record.ma_dinh_danh
                else:
                    # Cho form mới, tính mã dựa trên họ tên và số tiếp theo
                    record.ma_dinh_danh_preview = self._get_next_employee_code(record.ho_ten_dem, record.ten)
            else:
                record.ma_dinh_danh_preview = ''
    
    @api.depends("ngay_sinh")
    def _compute_tinh_tuoi(self): 
        for record in self:
            if record.ngay_sinh:  # Kiểm tra nếu trường ngay_sinh tồn tại
                year_now = datetime.now().year  
                record.tuoi = year_now - record.ngay_sinh.year 
    
    @api.depends('ho_ten_dem', 'ten')
    def _compute_ho_va_ten(self):
        for record in self:
            record.ho_va_ten = (record.ho_ten_dem or '') + ' ' + (record.ten or '')
            
    @api.constrains("tuoi")
    def _check_tuoi(self):
        for record in self: # self là tập hợp tất cả bản ghi, record là bản ghi hiện tại
            if record.tuoi < 18:
                raise ValidationError("Tuổi không được nhỏ hơn 18")

    @api.model_create_multi
    def create(self, vals_list):
        sequence = self.env['ir.sequence'].search([('code', '=', 'nhan_vien.sequence')], limit=1)
        for vals in vals_list:
            if not vals.get('ma_dinh_danh'):
                ho_ten_dem = vals.get('ho_ten_dem', '')
                ten = vals.get('ten', '')
                
                # Loại bỏ dấu
                ho_ten_dem_no_accent = self._remove_accents(ho_ten_dem)
                ten_no_accent = self._remove_accents(ten)
                
                # Lấy chữ cái đầu của từng từ trong họ tên đệm
                initials = ''.join([word[0].upper() for word in ho_ten_dem_no_accent.strip().split() if word])
                # Lấy tên (từ cuối) với chữ cái đầu hoa
                name_part = ten_no_accent.strip().capitalize() if ten_no_accent else ''
                
                # Lấy số thứ tự từ sequence
                next_num = sequence.number_next if sequence else 1
                
                # Sinh mã
                vals['ma_dinh_danh'] = f'{initials}{name_part}{next_num:03d}'
                
                # Tăng counter sequence cho record tiếp theo
                if sequence:
                    sequence.number_next = next_num + 1
        return super().create(vals_list)
