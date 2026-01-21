from odoo import models, fields, api
from datetime import datetime, time
from odoo.exceptions import ValidationError
from pytz import timezone, UTC

class TrangThaiChamCong(models.Model):
    _name = 'trang_thai_cham_cong'
    _description = 'Trạng thái chấm công'

    name = fields.Char(string="Tên trạng thái", required=True)


class BangChamCong(models.Model):
    _name = 'bang_cham_cong'
    _description = "Bảng chấm công"
    _rec_name = 'Id_BCC'

    # Basic fields
    nhan_vien_id = fields.Many2one('nhan_vien', string="Nhân viên", required=True)
    ngay_cham_cong = fields.Date("Ngày chấm công", required=True)

    Id_BCC = fields.Char(string="ID BCC", compute="_compute_Id_BCC", store=True)

    @api.depends('nhan_vien_id', 'ngay_cham_cong')
    def _compute_Id_BCC(self):
        for record in self:
            if record.nhan_vien_id and record.ngay_cham_cong:
                record.Id_BCC = f"{record.nhan_vien_id.ho_ten}_{record.ngay_cham_cong.strftime('%Y-%m-%d')}"
            else:
                record.Id_BCC = ""
    
    # Đăng ký ca làm
    dang_ky_ca_lam_id = fields.Many2one('dang_ky_ca_lam_theo_ngay', string="Đăng ký ca làm")
    ca_lam = fields.Selection(related='dang_ky_ca_lam_id.ca_lam', store=True, string="Ca làm")

    @api.onchange('nhan_vien_id', 'ngay_cham_cong')
    def _onchange_dang_ky_ca_lam(self):
        for record in self:
            if record.nhan_vien_id and record.ngay_cham_cong:
                dk_ca_lam = self.env['dang_ky_ca_lam_theo_ngay'].search([
                    ('nhan_vien_id', '=', record.nhan_vien_id.id),
                    ('ngay_lam', '=', record.ngay_cham_cong)
                ], limit=1)
                record.dang_ky_ca_lam_id = dk_ca_lam.id if dk_ca_lam else False
            else:
                record.dang_ky_ca_lam_id = False

    @api.model
    def create(self, vals):
        # Xử lý dang_ky_ca_lam_id
        if vals.get('nhan_vien_id') and vals.get('ngay_cham_cong'):
            # Tìm đăng ký ca làm
            dk_ca_lam = self.env['dang_ky_ca_lam_theo_ngay'].search([
                ('nhan_vien_id', '=', vals['nhan_vien_id']),
                ('ngay_lam', '=', vals['ngay_cham_cong'])
            ], limit=1)
            if dk_ca_lam:
                vals['dang_ky_ca_lam_id'] = dk_ca_lam.id
            
            # Tìm đơn từ
            don_tu = self.env['don_tu'].search([
                ('nhan_vien_id', '=', vals['nhan_vien_id']),
                ('ngay_ap_dung', '=', vals['ngay_cham_cong']),
                ('trang_thai_duyet', '=', 'da_duyet'),
                ('loai_don', 'in', ['di_muon', 've_som', 'nghi']),

            ], limit=1)
            if don_tu:
                vals['don_tu_id'] = don_tu.id
            
        return super(BangChamCong, self).create(vals)

    def write(self, vals):
        """Ngăn sửa khi bảng chấm công bị khóa + cập nhật dang_ky_ca_lam_id và don_tu_id"""
        # Kiểm tra khóa
        for record in self:
            if record.is_locked and vals:
                raise ValidationError("Bảng chấm công này đã bị khóa, không thể sửa đổi!")
        
        # Trước khi lưu, cập nhật dang_ky_ca_lam_id và don_tu_id nếu cần
        for record in self:
            # Lấy giá trị mới hoặc giữ giá trị cũ
            nhan_vien_id = vals.get('nhan_vien_id', record.nhan_vien_id.id)
            ngay_cham_cong = vals.get('ngay_cham_cong', record.ngay_cham_cong)
            
            if nhan_vien_id and ngay_cham_cong:
                # Tìm đăng ký ca làm
                dk_ca_lam = self.env['dang_ky_ca_lam_theo_ngay'].search([
                    ('nhan_vien_id', '=', nhan_vien_id),
                    ('ngay_lam', '=', ngay_cham_cong)
                ], limit=1)
                if dk_ca_lam:
                    vals['dang_ky_ca_lam_id'] = dk_ca_lam.id
            
                # Tìm đơn từ
                don_tu = self.env['don_tu'].search([
                    ('nhan_vien_id', '=', nhan_vien_id),
                    ('ngay_ap_dung', '=', ngay_cham_cong),
                    ('trang_thai_duyet', '=', 'da_duyet'),
                    ('loai_don', 'in', ['di_muon', 've_som', 'nghi']),

                ], limit=1)
                if don_tu:
                    vals['don_tu_id'] = don_tu.id
        
        # Lưu dữ liệu
        result = super(BangChamCong, self).write(vals)
        
        # Invalidate cache để bắt Odoo tính lại các computed fields
        self.invalidate_cache()
        
        return result

    # Thời gian làm việc
    gio_vao_ca = fields.Datetime("Giờ vào ca", compute='_compute_gio_ca', store=True, readonly=True)
    gio_ra_ca = fields.Datetime("Giờ ra ca", compute='_compute_gio_ca', store=True, readonly=True)
    
    @api.depends('ca_lam', 'ngay_cham_cong', 'dang_ky_ca_lam_id')
    def _compute_gio_ca(self):
        for record in self:
            if not record.ngay_cham_cong or not record.ca_lam:
                record.gio_vao_ca = False
                record.gio_ra_ca = False
                continue

            user_tz = self.env.user.tz or 'UTC'
            tz = timezone(user_tz)

            if record.ca_lam == "Sáng":
                gio_vao = time(7, 30)  # 7:30 AM
                gio_ra = time(11, 30)  # 11:30 AM
            elif record.ca_lam == "Chiều":
                gio_vao = time(13, 30)  # 1:30 PM
                gio_ra = time(17, 30)  # 5:30 PM
            elif record.ca_lam == "Cả ngày":
                gio_vao = time(7, 30)  # 7:30 AM
                gio_ra = time(17, 30)  # 5:30 PM
            else:
                record.gio_vao_ca = False
                record.gio_ra_ca = False
                continue

            # Convert to datetime in user's timezone
            thoi_gian_vao = datetime.combine(record.ngay_cham_cong, gio_vao)
            thoi_gian_ra = datetime.combine(record.ngay_cham_cong, gio_ra)
            
            # Store in UTC
            record.gio_vao_ca = tz.localize(thoi_gian_vao).astimezone(UTC).replace(tzinfo=None)
            record.gio_ra_ca = tz.localize(thoi_gian_ra).astimezone(UTC).replace(tzinfo=None)

    gio_vao = fields.Datetime("Giờ vào thực tế")
    gio_ra = fields.Datetime("Giờ ra thực tế")

    # Tính toán đi muộn
    phut_di_muon_goc = fields.Float("Số phút đi muộn gốc", compute="_compute_phut_di_muon_goc", store=True, readonly=True)
    phut_di_muon = fields.Float("Số phút đi muộn thực tế", compute="_compute_phut_di_muon", store=True, readonly=True)
    
    @api.depends('gio_vao', 'gio_vao_ca')
    def _compute_phut_di_muon_goc(self):
        for record in self:
            if record.gio_vao and record.gio_vao_ca:
                delta = record.gio_vao - record.gio_vao_ca
                record.phut_di_muon_goc = max(0, delta.total_seconds() / 60)
            else:
                record.phut_di_muon_goc = 0

    @api.depends('phut_di_muon_goc', 'don_tu_id', 'loai_don', 'thoi_gian_xin')
    def _compute_phut_di_muon(self):
        for record in self:
            record.phut_di_muon = record.phut_di_muon_goc
            
            # Nếu có đơn từ được duyệt
            if record.don_tu_id and record.don_tu_id.trang_thai_duyet == 'da_duyet':
                if record.loai_don == 'di_muon':
                    record.phut_di_muon = max(0, record.phut_di_muon_goc - record.thoi_gian_xin)

    # Tính toán về sớm
    phut_ve_som_goc = fields.Float("Số phút về sớm gốc", compute="_compute_phut_ve_som_goc", store=True, readonly=True)
    phut_ve_som = fields.Float("Số phút về sớm thực tế", compute="_compute_phut_ve_som", store=True, readonly=True)
    
    @api.depends('gio_ra', 'gio_ra_ca')
    def _compute_phut_ve_som_goc(self):
        for record in self:
            if record.gio_ra and record.gio_ra_ca:
                delta = record.gio_ra_ca - record.gio_ra
                record.phut_ve_som_goc = max(0, delta.total_seconds() / 60)
            else:
                record.phut_ve_som_goc = 0

    @api.depends('phut_ve_som_goc', 'don_tu_id', 'loai_don', 'thoi_gian_xin')
    def _compute_phut_ve_som(self):
        for record in self:
            record.phut_ve_som = record.phut_ve_som_goc
            
            # Nếu có đơn từ được duyệt
            if record.don_tu_id and record.don_tu_id.trang_thai_duyet == 'da_duyet':
                if record.loai_don == 've_som':
                    record.phut_ve_som = max(0, record.phut_ve_som_goc - record.thoi_gian_xin)
                

    # Trạng thái chấm công
    trang_thai = fields.Selection([
        ('di_lam', 'Đi làm'),
        ('di_muon', 'Đi muộn'),
        ('di_muon_ve_som', 'Đi muộn và về sớm'),
        ('ve_som', 'Về sớm'),
        ('vang_mat', 'Vắng mặt'),
        ('vang_mat_co_phep', 'Vắng mặt có phép'),
    ], string="Trạng thái", compute="_compute_trang_thai", store=True, readonly=True)
    
    @api.depends('phut_di_muon', 'phut_ve_som', 'gio_vao', 'gio_ra')
    def _compute_trang_thai(self):
        for record in self:
            if not record.gio_vao and not record.gio_ra:
                record.trang_thai = 'vang_mat'
            elif record.phut_di_muon > 0 and record.phut_ve_som > 0:
                record.trang_thai = 'di_muon_ve_som'
            elif record.phut_di_muon > 0:
                record.trang_thai = 'di_muon'
            elif record.phut_ve_som > 0:
                record.trang_thai = 've_som'
            else:
                record.trang_thai = 'di_lam'

    # Đơn từ liên quan
    don_tu_id = fields.Many2one('don_tu', string="Đơn từ")
    loai_don = fields.Selection(string='Loại đơn',related='don_tu_id.loai_don')
    thoi_gian_xin = fields.Float(string='Thời gian xin',related='don_tu_id.thoi_gian_xin')
    
    @api.onchange('nhan_vien_id', 'ngay_cham_cong')
    def _onchange_don_tu(self):
        for record in self:
            if record.nhan_vien_id and record.ngay_cham_cong:
                don_tu = self.env['don_tu'].search([
                    ('nhan_vien_id', '=', record.nhan_vien_id.id),
                    ('ngay_ap_dung', '=', record.ngay_cham_cong),
                    ('trang_thai_duyet', '=', 'da_duyet'),
                    ('loai_don', 'in', ['di_muon', 've_som', 'nghi']),

                ], limit=1)
                record.don_tu_id = don_tu.id if don_tu else False
            else:
                record.don_tu_id = False

    @api.onchange('gio_vao', 'gio_ra', 'don_tu_id')
    def _onchange_update_trang_thai(self):
        """Trigger recompute trang_thai khi user thay đổi giờ vào/ra hoặc đơn từ trong form"""
        for record in self:
            # Force Odoo recompute các dependent fields
            if record.gio_vao or record.gio_ra or record.don_tu_id:
                # Trực tiếp tính toán lại để form update ngay
                if record.gio_vao and record.gio_vao_ca:
                    delta_muon = record.gio_vao - record.gio_vao_ca
                    phut_di_muon_goc = max(0, delta_muon.total_seconds() / 60)
                else:
                    phut_di_muon_goc = 0

                if record.gio_ra and record.gio_ra_ca:
                    delta_som = record.gio_ra_ca - record.gio_ra
                    phut_ve_som_goc = max(0, delta_som.total_seconds() / 60)
                else:
                    phut_ve_som_goc = 0

                # Áp dụng đơn từ nếu có
                phut_di_muon = phut_di_muon_goc
                phut_ve_som = phut_ve_som_goc

                if record.don_tu_id and record.don_tu_id.trang_thai_duyet == 'da_duyet':
                    if record.loai_don == 'di_muon':
                        phut_di_muon = max(0, phut_di_muon_goc - record.thoi_gian_xin)
                    elif record.loai_don == 've_som':
                        phut_ve_som = max(0, phut_ve_som_goc - record.thoi_gian_xin)

                # Cập nhật trang_thai
                if not record.gio_vao and not record.gio_ra:
                    record.trang_thai = 'vang_mat'
                elif phut_di_muon > 0 and phut_ve_som > 0:
                    record.trang_thai = 'di_muon_ve_som'
                elif phut_di_muon > 0:
                    record.trang_thai = 'di_muon'
                elif phut_ve_som > 0:
                    record.trang_thai = 've_som'
                else:
                    record.trang_thai = 'di_lam'

    # Thêm trường mới để tính công, OT
    so_cong = fields.Float(string="Số công", default=0.0, compute="_compute_so_cong", store=True, readonly=True,
                           help="Tính dựa trên trạng thái: vắng mặt=0, có phép=0.5, đi làm/muộn/sớm=1")
    ot_gio = fields.Float(string="Giờ OT", default=0.0,
                          help="Giờ làm thêm ngoài giờ")
    
    # Khóa bảng chấm công (khi tính công)
    is_locked = fields.Boolean(string="Khóa", default=False,
                               help="Khóa để ngăn chặn sửa đổi khi đã tính công")
    @api.depends('trang_thai', 'don_tu_id')
    def _compute_so_cong(self):
        for r in self:
            if r.trang_thai == 'vang_mat':
                r.so_cong = 0.0
            elif r.trang_thai == 'vang_mat_co_phep':
                r.so_cong = 0.5
            else:
                r.so_cong = 1.0
    
    
    @api.model_create_multi
    def create(self, vals_list):
        """Ngăn tạo mới khi bảng chấm công bị khóa"""
        for vals in vals_list:
            if vals.get('ngay_cham_cong') and vals.get('nhan_vien_id'):
                existing = self.search([
                    ('ngay_cham_cong', '=', vals['ngay_cham_cong']),
                    ('nhan_vien_id', '=', vals['nhan_vien_id']),
                    ('is_locked', '=', True),
                ])
                if existing:
                    raise ValidationError("Bảng chấm công này đã bị khóa, không thể tạo mới!")
        return super().create(vals_list)