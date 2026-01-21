from odoo import http
from odoo.http import request

def _check_token():
    token = request.httprequest.headers.get("X-API-KEY")
    saved = request.env["ir.config_parameter"].sudo().get_param("tinhluong.api_key")
    return bool(token) and token == saved

class TinhLuongAPI(http.Controller):

    @http.route("/api/v1/attendance/import", type="json", auth="none", methods=["POST"], csrf=False)
    def import_attendance(self, items):
        if not _check_token():
            return {"ok": False, "error": "Unauthorized"}

        ChamCong = request.env["cham_cong"].sudo()
        NhanVien = request.env["nhan_vien"].sudo()

        created = 0
        for it in items:
            # it: {"ma_dinh_danh":"NV01","thang":12,"nam":2025,"so_cong":26,"ot_gio":10}
            nv = NhanVien.search([("ma_dinh_danh", "=", it.get("ma_dinh_danh"))], limit=1)
            if not nv:
                continue

            ChamCong.create({
                "nhan_vien_id": nv.id,
                "thang": int(it["thang"]),
                "nam": int(it["nam"]),
                "so_cong": float(it.get("so_cong", 0)),
                "ot_gio": float(it.get("ot_gio", 0)),
            })
            created += 1

        return {"ok": True, "created": created}

    @http.route("/api/v1/payroll/export", type="json", auth="none", methods=["POST"], csrf=False)
    def export_payroll(self, thang, nam):
        if not _check_token():
            return {"ok": False, "error": "Unauthorized"}

        sheet = request.env["bang_luong"].sudo().search([("thang", "=", int(thang)), ("nam", "=", int(nam))], limit=1)
        if not sheet:
            return {"ok": False, "error": "Not found"}

        return {
            "ok": True,
            "period": {"thang": sheet.thang, "nam": sheet.nam, "state": sheet.state},
            "totals": {"gross": sheet.tong_gross, "net": sheet.tong_net},
            "lines": [
                {
                    "ma_dinh_danh": l.nhan_vien_id.ma_dinh_danh,
                    "ho_ten": l.nhan_vien_id.ho_ten,
                    "so_cong": l.so_cong,
                    "ot_gio": l.ot_gio,
                    "gross": l.gross,
                    "net": l.net,
                    "ai_flag": l.ai_flag,
                    "ai_note": l.ai_note,
                }
                for l in sheet.line_ids
            ],
        }
