# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class NgayTraLuong(models.Model):
    _name = "tinh_luong.ngay_tra_luong"
    _description = "Ngày trả lương"
    _rec_name = "dot_lam_viec_id"
    _order = "ngay_tra desc"
    dot_lam_viec_id = fields.Many2one("dot_dang_ky", string="Đợt làm việc")

    ten_dot_chi_tra = fields.Char(string="Tên đợt chi trả")

    ngay_tra = fields.Date(string="Ngày trả lương", required=True)
    
    google_calendar_event_id = fields.Char(string="Google Calendar Event ID", readonly=True)
    sync_calendar_status = fields.Selection([
        ('not_synced', 'Chưa đồng bộ'),
        ('synced', 'Đã đồng bộ'),
        ('error', 'Lỗi đồng bộ'),
    ], string="Trạng thái đồng bộ", default='not_synced')

    @api.constrains("dot_lam_viec_id")
    def _check_period_not_past(self):
        for rec in self:
            if not rec.dot_lam_viec_id:
                continue
            # dot_dang_ky is expected to have ngay_ket_thuc (end date)
            end = getattr(rec.dot_lam_viec_id, "ngay_ket_thuc", False)
            if end:
                today = fields.Date.context_today(rec)
                if end < today:
                    raise ValidationError(_("Không thể chọn đợt làm việc đã kết thúc (quá khứ)."))

    @api.onchange("dot_lam_viec_id")
    def _onchange_dot_lam_viec_id(self):
        if not self.dot_lam_viec_id:
            return
        end = getattr(self.dot_lam_viec_id, "ngay_ket_thuc", False)
        if end and end < fields.Date.context_today(self):
            return {
                "warning": {
                    "title": _("Đợt làm việc đã kết thúc"),
                    "message": _("Bạn đã chọn một đợt làm việc ở quá khứ."),
                }
            }

    @api.constrains("dot_lam_viec_id", "ngay_tra")
    def _check_ngay_tra_within_period(self):
        """Require `ngay_tra` to be not earlier than the period start.
        This allows dates inside the period and in months after the period,
        but disallows dates before the period start.
        """
        for rec in self:
            if not rec.dot_lam_viec_id or not rec.ngay_tra:
                continue
            start = getattr(rec.dot_lam_viec_id, "ngay_bat_dau", False)
            if start:
                try:
                    ngay_tra_date = fields.Date.from_string(rec.ngay_tra)
                    start_date = fields.Date.from_string(start)
                except Exception:
                    continue
                if ngay_tra_date < start_date:
                    raise ValidationError(_("Ngày trả lương không được nằm trước ngày bắt đầu của đợt làm việc đã chọn."))

    @api.onchange("dot_lam_viec_id", "ngay_tra")
    def _onchange_dot_and_ngay_tra(self):
        if not self.dot_lam_viec_id or not self.ngay_tra:
            return
        start = getattr(self.dot_lam_viec_id, "ngay_bat_dau", False)
        end = getattr(self.dot_lam_viec_id, "ngay_ket_thuc", False)
        if start:
            try:
                ngay_tra_date = fields.Date.from_string(self.ngay_tra)
                start_date = fields.Date.from_string(start)
            except Exception:
                return
            if ngay_tra_date < start_date:
                return {
                    "warning": {
                        "title": _("Ngày trả lương không hợp lệ"),
                        "message": _("Ngày trả lương không được nằm trước ngày bắt đầu của đợt làm việc đã chọn."),
                    }
                }
    def action_sync_to_google_calendar(self):
        """Tạo sự kiện trên Google Calendar qua Odoo Calendar"""
        from datetime import datetime, timedelta
        
        for rec in self:
            try:
                # Kiểm tra user có access token Google chưa
                user = self.env.user
                if not hasattr(user, 'google_calendar_rtoken') or not user.google_calendar_rtoken:
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'title': _('Chưa kết nối Google'),
                            'message': _('Vui lòng kết nối Google Calendar:\n1. Click Avatar → My Profile\n2. Click Edit\n3. Tìm "Authenticate with Google" và click\n4. Đăng nhập Google\n5. Save'),
                            'type': 'warning',
                        }
                    }
                
                # Tạo event qua Odoo Calendar model
                event_title = f"Trả lương - {rec.ten_dot_chi_tra or 'Đợt làm việc'}"
                event_description = f"Ngày trả lương cho đợt: {rec.dot_lam_viec_id.ten_dot if rec.dot_lam_viec_id else ''}"
                
                # Thời gian sự kiện (cả ngày)
                event_start = datetime.combine(rec.ngay_tra, datetime.min.time())
                event_end = datetime.combine(rec.ngay_tra, datetime.min.time()) + timedelta(days=1)
                
                # Tạo event trong Odoo Calendar
                calendar_event = self.env['calendar.event'].create({
                    'name': event_title,
                    'description': event_description,
                    'start': event_start,
                    'stop': event_end,
                    'user_id': user.id,
                    'allday': True,
                })
                
                # Đánh dấu là đã sync
                rec.google_calendar_event_id = calendar_event.id
                rec.sync_calendar_status = 'synced'
                
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Thành công'),
                        'message': _('Đã tạo sự kiện trên Odoo Calendar. Sự kiện sẽ tự động sync lên Google Calendar'),
                        'type': 'success',
                    }
                }
                
            except Exception as e:
                rec.sync_calendar_status = 'error'
                import traceback
                error_detail = traceback.format_exc()
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Lỗi'),
                        'message': _('Không thể tạo sự kiện: %s') % str(e),
                        'type': 'danger',
                    }
                }