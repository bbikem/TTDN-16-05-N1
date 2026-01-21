from odoo import models, fields, api
from odoo.exceptions import ValidationError


class AIRule(models.Model):
    _name = "ai_rule"
    _description = "Cấu hình AI (phát hiện bất thường)"
    _rec_name = "name"
    _inherit = ["mail.thread", "mail.activity.mixin"]  # log thay đổi

    name = fields.Char(string="Tên cấu hình", default="AI Rule", required=True, tracking=True)

    max_cong = fields.Float(string="Ngưỡng công tối đa", default=26.0, tracking=True)
    max_ot_gio = fields.Float(string="Ngưỡng OT tối đa (giờ)", default=40.0, tracking=True)
    max_net = fields.Float(string="Ngưỡng NET tối đa", default=50000000.0, tracking=True)

    @api.constrains("max_cong", "max_ot_gio", "max_net")
    def _check_thresholds(self):
        for r in self:
            if r.max_cong < 0:
                raise ValidationError("Ngưỡng công tối đa không được âm.")
            if r.max_ot_gio < 0:
                raise ValidationError("Ngưỡng OT tối đa không được âm.")
            if r.max_net < 0:
                raise ValidationError("Ngưỡng NET tối đa không được âm.")

    @classmethod
    def get_singleton(cls, env):
        rule = env["ai_rule"].sudo().search([], limit=1)
        if not rule:
            rule = env["ai_rule"].sudo().create({})
        return rule

    @api.model
    def create(self, vals):
        # Singleton: chỉ cho tồn tại 1 bản ghi
        if self.search_count([]) >= 1:
            raise ValidationError("Chỉ được phép có 1 cấu hình AI Rule.")
        return super().create(vals)

    def action_open_singleton(self):
        rule = self.get_singleton(self.env)
        return {
            "type": "ir.actions.act_window",
            "name": "Cấu hình AI Rule",
            "res_model": "ai_rule",
            "view_mode": "form",
            "res_id": rule.id,
            "target": "current",
        }
