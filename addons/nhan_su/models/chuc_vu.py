from odoo import models, fields, api

class ChucVu(models.Model):
    _name = 'chuc_vu'
    _description = 'Bảng chứa thông tin chức vụ'
    _rec_name = 'ten_chuc_vu'

    ma_chuc_vu = fields.Char("Mã chức vụ", readonly=True, store=True)
    ten_chuc_vu = fields.Char("Tên chức vụ", required=True)
    ma_chuc_vu_preview = fields.Char("Mã chức vụ dự kiến", compute="_compute_ma_chuc_vu_preview", store=False, readonly=True)
    luong_co_ban = fields.Float("Lương cơ bản", default=0.0, help="Lương cơ bản cho chức vụ này (mặc định cho nhân viên có chức vụ này)")

    def _format_salary_input(self, value):
        """Chuyển đổi định dạng lương từ chuỗi thành số"""
        if isinstance(value, str):
            # Loại bỏ dấu cách và dấu phẩy
            value = value.replace(' ', '').replace(',', '')
        try:
            return float(value)
        except (ValueError, TypeError):
            return 0.0

    def _get_next_sequence_number(self):
        """Lấy số tiếp theo của sequence mà không tăng counter"""
        sequence = self.env['ir.sequence'].search([('code', '=', 'chuc_vu.sequence')], limit=1)
        if sequence:
            return sequence.number_next
        return 1

    @api.depends('ten_chuc_vu')
    def _compute_ma_chuc_vu_preview(self):
        for record in self:
            if record.ten_chuc_vu:
                # Nếu đã có ID (record lưu rồi), lấy mã từ DB
                if record.id and record.ma_chuc_vu:
                    record.ma_chuc_vu_preview = record.ma_chuc_vu
                else:
                    # Cho form mới, tính mã dựa trên số tiếp theo
                    next_num = self._get_next_sequence_number()
                    preview_code = f'CV{next_num:05d}'
                    record.ma_chuc_vu_preview = preview_code
            else:
                record.ma_chuc_vu_preview = ''

    @api.model_create_multi
    def create(self, vals_list):
        sequence = self.env['ir.sequence'].search([('code', '=', 'chuc_vu.sequence')], limit=1)
        for vals in vals_list:
            # Xử lý định dạng lương cơ bản
            if 'luong_co_ban' in vals:
                vals['luong_co_ban'] = self._format_salary_input(vals['luong_co_ban'])
            
            if not vals.get('ma_chuc_vu'):
                # Lấy số tiếp theo và sinh mã
                next_num = sequence.number_next if sequence else 1
                vals['ma_chuc_vu'] = f'CV{next_num:05d}'
                # Tăng counter sequence cho record tiếp theo
                if sequence:
                    sequence.number_next = next_num + 1
        return super().create(vals_list)

    def write(self, vals):
        # Xử lý định dạng lương cơ bản
        if 'luong_co_ban' in vals:
            vals['luong_co_ban'] = self._format_salary_input(vals['luong_co_ban'])
        return super().write(vals)