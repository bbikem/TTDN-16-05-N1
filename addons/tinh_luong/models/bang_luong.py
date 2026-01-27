# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class BangLuong(models.Model):
    _name = "tinh_luong.bang_luong"
    _description = "Bảng lương"
    _rec_name = "nhan_vien_id"
    _order = "id desc"

    nhan_vien_id = fields.Many2one("nhan_vien", string="Nhân viên", required=True)
    dot_lam_viec_id = fields.Many2one("dot_dang_ky", string="Đợt làm việc", required=True)
    ngay_chot = fields.Date(string="Ngày chốt lương", default=fields.Date.context_today)

    so_ngay_di_lam = fields.Integer(string="Số ngày đi làm", compute="_compute_attendance_metrics", store=True)
    so_gio_lam_viec = fields.Float(string="Số giờ làm việc", compute="_compute_attendance_metrics", store=True)
    so_ngay_di_muon = fields.Integer(string="Số ngày đi muộn", compute="_compute_attendance_metrics", store=True)

    luong_co_ban = fields.Float(string="Lương cơ bản (tháng)", default=0.0)
    luong_theo_ngay = fields.Float(string="Lương theo ngày", compute="_compute_salary", store=True)

    muc_phat_moi_ngay_di_muon = fields.Float(string="Phạt mỗi ngày đi muộn", default=100000.0)
    tien_phat_di_muon = fields.Float(string="Tiền phạt đi muộn", compute="_compute_salary", store=True)

    tro_cap_ids = fields.One2many("tinh_luong.tro_cap", "bang_luong_id", string="Danh sách trợ cấp")
    tong_tro_cap = fields.Float(string="Tổng trợ cấp", compute="_compute_salary", store=True)

    tong_luong = fields.Float(string="Tổng lương", compute="_compute_salary", store=True)
    thuc_lanh = fields.Float(string="Thực lãnh", compute="_compute_salary", store=True)

    state = fields.Selection([
        ("draft", "Nháp"),
        ("confirmed", "Đã xác nhận"),
        ("paid", "Đã trả"),
        ("cancel", "Hủy"),
    ], string="Trạng thái", default="draft", tracking=True)

    ghi_chu = fields.Text(string="Ghi chú")

    @api.onchange("nhan_vien_id")
    def _onchange_nhan_vien(self):
        if not self.nhan_vien_id:
            return
        # Lấy lương cơ bản từ chức vụ của nhân viên
        if self.nhan_vien_id.chuc_vu_id and self.nhan_vien_id.chuc_vu_id.luong_co_ban:
            self.luong_co_ban = self.nhan_vien_id.chuc_vu_id.luong_co_ban
        # Mapping mềm (nếu có sẵn field ở nhân viên)
        elif hasattr(self.nhan_vien_id, "luong_co_ban") and self.nhan_vien_id.luong_co_ban:
            self.luong_co_ban = self.nhan_vien_id.luong_co_ban

    @api.model_create_multi
    def create(self, vals_list):
        """Tự động set luong_co_ban từ chuc_vu khi tạo record"""
        for vals in vals_list:
            if vals.get('nhan_vien_id') and not vals.get('luong_co_ban'):
                nhan_vien = self.env['nhan_vien'].browse(vals['nhan_vien_id'])
                if nhan_vien.chuc_vu_id and nhan_vien.chuc_vu_id.luong_co_ban:
                    vals['luong_co_ban'] = nhan_vien.chuc_vu_id.luong_co_ban
        return super().create(vals_list)

    @api.depends("nhan_vien_id", "dot_lam_viec_id")
    def _compute_attendance_metrics(self):
        for rec in self:
            rec.so_ngay_di_lam = 0
            rec.so_gio_lam_viec = 0.0
            rec.so_ngay_di_muon = 0

            if not rec.nhan_vien_id or not rec.dot_lam_viec_id:
                continue

            # Lấy ngày bắt đầu và kết thúc từ đợt làm việc
            start = rec.dot_lam_viec_id.ngay_bat_dau
            end = rec.dot_lam_viec_id.ngay_ket_thuc
            if not start or not end:
                continue

            # Tìm kiếm bảng chấm công của nhân viên trong khoảng thời gian này
            BangChamCong = self.env["bang_cham_cong"]
            domain = [
                ("nhan_vien_id", "=", rec.nhan_vien_id.id),
                ("ngay_cham_cong", ">=", start),
                ("ngay_cham_cong", "<=", end)
            ]
            lines = BangChamCong.search(domain)

            so_ngay = 0
            gio_lam = 0.0
            so_ngay_di_muon = 0

            for l in lines:
                # Đếm ngày đi làm dựa vào trạng thái
                # Chỉ tính ngày đi làm thực tế (trạng thái di_lam, không tính vang mặt)
                if l.trang_thai and l.trang_thai not in ("vang_mat", "vang_mat_co_phep"):
                    so_ngay += 1

                # Tính giờ làm từ giờ vào và giờ ra thực tế
                if l.gio_vao and l.gio_ra:
                    delta = (l.gio_ra - l.gio_vao).total_seconds() / 3600.0
                    if delta > 0:
                        gio_lam += delta

                # Đếm số ngày có đi muộn (chỉ cần có phut_di_muon > 0 là tính 1 ngày)
                if l.phut_di_muon and l.phut_di_muon > 0:
                    so_ngay_di_muon += 1

            rec.so_ngay_di_lam = so_ngay
            rec.so_gio_lam_viec = round(gio_lam, 2)
            rec.so_ngay_di_muon = so_ngay_di_muon

    @api.depends(
        "nhan_vien_id",
        "dot_lam_viec_id",
        "luong_co_ban",
        "so_ngay_di_lam", 
        "so_ngay_di_muon",
        "muc_phat_moi_ngay_di_muon",
        "tro_cap_ids.so_tien"
    )
    def _compute_salary(self):
        for rec in self:
            # Tính lương theo ngày (26 ngày làm việc/tháng)
            luong_theo_ngay = (rec.luong_co_ban / 26.0) if rec.luong_co_ban else 0.0
            
            # Tính tổng lương = lương theo ngày x số ngày đi làm thực tế
            tong_luong = luong_theo_ngay * rec.so_ngay_di_lam if luong_theo_ngay else 0.0
            
            # Tính tổng trợ cấp
            tong_tro_cap = sum(rec.tro_cap_ids.mapped("so_tien")) if rec.tro_cap_ids else 0.0

            # Tính tiền phạt đi muộn (số ngày đi muộn x mức phạt/ngày)
            tien_phat = (rec.so_ngay_di_muon or 0) * (rec.muc_phat_moi_ngay_di_muon or 0.0)

            # Thực lãnh = Tổng lương + Trợ cấp - Phạt
            thuc_lanh = tong_luong + tong_tro_cap - tien_phat

            rec.luong_theo_ngay = luong_theo_ngay
            rec.tong_tro_cap = tong_tro_cap
            rec.tong_luong = tong_luong
            rec.tien_phat_di_muon = tien_phat
            rec.thuc_lanh = thuc_lanh

    def action_confirm(self):
        for rec in self:
            if rec.state == "draft":
                rec.state = "confirmed"

    def action_paid(self):
        for rec in self:
            if rec.state == "confirmed":
                rec.state = "paid"

    def action_cancel(self):
        for rec in self:
            rec.state = "cancel"

    def action_reset_draft(self):
        for rec in self:
            rec.state = "draft"

    @api.constrains("dot_lam_viec_id", "nhan_vien_id")
    def _check_unique_employee_period(self):
        for rec in self:
            if not rec.nhan_vien_id or not rec.dot_lam_viec_id:
                continue
            dup = self.search_count([
                ("id", "!=", rec.id),
                ("nhan_vien_id", "=", rec.nhan_vien_id.id),
                ("dot_lam_viec_id", "=", rec.dot_lam_viec_id.id),
                ("state", "!=", "cancel"),
            ])
            if dup:
                raise ValidationError(_("Nhân viên đã có bảng lương trong đợt làm việc này."))
