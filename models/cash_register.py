from odoo import models, fields, api
from odoo.exceptions import UserError

class CashRegister(models.Model):
    _name = 'cash.register'
    _description = 'Registre de caisse'
    
    name = fields.Char(string='Mois', required=True)
    opening_balance = fields.Float(string='Balance d\'ouverture', required=True)
    current_balance = fields.Float(string='Balance courante', compute='_compute_current_balance', store=True)
    state = fields.Selection([('draft', 'En cours'),
                              ('valide', 'Cloturé')], string='Etat', default='draft')
    line_ids = fields.One2many('cash.register.line', 'register_id', string='Lines')
    journal_id = fields.Many2one('account.journal', string='Journal', required=True)
    date = fields.Date(string='Date', required=True)
    company_id = fields.Many2one('res.company', string='Société', required=True, default=lambda self: self.env.company)
    
    @api.depends('line_ids.balance')
    def _compute_current_balance(self):
        for record in self:
            record.current_balance = record.opening_balance - sum(line.balance for line in record.line_ids)
    
    @api.model
    def create(self, vals):
        # Utiliser read_group pour obtenir la somme des soldes du compte 530000
        account_move_line_530000 = self.env['account.move.line'].read_group(
            [('account_id.code', '=', '530000'), ('company_id', '=', self.env.user.company_id.id)],
            ['balance'],
            []
        )
        opening_balance = sum(line['balance'] for line in account_move_line_530000) if account_move_line_530000 else 0
        vals['opening_balance'] = opening_balance
        return super(CashRegister, self).create(vals)
    
    def write(self, vals):
        for record in self:
            if record.state == 'valide':
                raise UserError("Vous ne pouvez pas modifier un registre de caisse qui est déjà validé.")
        return super(CashRegister, self).write(vals)
    
    def close(self):
        for record in self:
            record.state = 'valide'

    def action_comptabiliser(self):
        for record in self:
            for line in record.line_ids:
                if line.status == 'draft':
                    move_vals = {
                        'date': line.date,
                        'journal_id': record.journal_id.id,  
                        'company_id': record.company_id.id,
                        'line_ids': [
                            (0, 0, {
                                'account_id': line.account_id.id,
                                'partner_id': line.partner_id.id,
                                'name': line.description,
                                'debit': line.debit if line.debit > 0 else 0.0,
                                'credit': 0.0,
                                'company_id': line.company_id.id,
                            }),
                            (0, 0, {
                                'account_id': self.env['account.account'].search([('code', '=', '530000'), ('company_id', '=', line.company_id.id)], limit=1).id,
                                'partner_id': line.partner_id.id,
                                'name': line.description,
                                'debit': 0.0,
                                'credit': line.debit if line.debit > 0 else line.credit,
                                'company_id': line.company_id.id,
                            }),
                        ]
                    }
                    move = self.env['account.move'].create(move_vals)
                    line.status = 'confirmed'
                    line.move_id = move.id

class CashRegisterLine(models.Model):
    _name = 'cash.register.line'
    _description = 'Registre de caisse détail'
    
    date = fields.Date(string='Date', required=True)
    partner_id = fields.Many2one('res.partner', string='Bénéficiaire', required=True, domain="[('company_id', '=', company_id)]")
    account_id = fields.Many2one('account.account', string='Compte', required=True, domain="[('company_id', '=', company_id)]")
    department_id = fields.Many2one('hr.department', string='Structure', domain="[('company_id', '=', company_id)]")
    description = fields.Text(string='Description', required=True)
    credit = fields.Float(string='Credit')
    debit = fields.Float(string='Debit')
    balance = fields.Float(string='Balance', compute='_compute_balance', store=True)
    status = fields.Selection([('draft', 'Brouillon'), ('confirmed', 'Confirmé')], string='Status', default='draft')
    register_id = fields.Many2one('cash.register', string='Registre de caisse', required=True)
    move_id = fields.Many2one('account.move', string='Pièce comptable', readonly=True)
    company_id = fields.Many2one('res.company', string='Société', required=True, default=lambda self: self.env.company)

    @api.depends('credit', 'debit')
    def _compute_balance(self):
        for line in self:
            line.balance = abs(line.debit - line.credit)
