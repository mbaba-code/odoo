from odoo import models, fields, api
from datetime import datetime, timedelta
import json
import logging

_logger = logging.getLogger(__name__)


class OnedeskAvailabilityCache(models.Model):
    """Cache for property/unit availability to speed up portal queries"""
    _name = 'onedesk.availability.cache'
    _description = 'Availability Cache'
    _rec_name = 'unit_id'

    # ========== RELATIONS ==========
    unit_id = fields.Many2one(
        'onedesk.unit',
        string='Unité',
        required=True,
        ondelete='cascade',
        index=True
    )

    property_id = fields.Many2one(
        'onedesk.property',
        string='Propriété',
        related='unit_id.property_id',
        store=True,
        readonly=True,
        index=True
    )

    company_id = fields.Many2one(
        'res.company',
        string='Entreprise',
        related='unit_id.property_id.company_id',
        store=True,
        readonly=True
    )

    # ========== CACHE DATA ==========
    start_date = fields.Date(string='Date début', required=True, index=True)
    end_date = fields.Date(string='Date fin', required=True)

    # Availability data in JSON format
    availability_data = fields.Text(
        string='Données de disponibilité (JSON)',
        help="Format: {'2025-11-22': 'available', '2025-11-23': 'booked'}"
    )

    # Price cache
    price_data = fields.Text(
        string='Données de prix (JSON)',
        help="Format: {'2025-11-22': 150.0, '2025-11-23': 150.0}"
    )

    # Booking data
    booking_data = fields.Text(
        string='Données de réservations (JSON)',
        help="Format: {'2025-11-22': ['RES001', 'RES002']}"
    )

    # ========== CACHE STATS ==========
    cache_hits = fields.Integer(string='Hits', default=0, readonly=True)
    cache_misses = fields.Integer(string='Misses', default=0, readonly=True)
    last_accessed = fields.Datetime(string='Dernier accès')
    created_date = fields.Datetime(string='Date création', default=fields.Datetime.now, readonly=True)
    expires_at = fields.Datetime(string='Expire le', readonly=True)
    is_valid = fields.Boolean(string='Valide', default=True, readonly=True)

    class Constraint(models.Constraint):
        _constraint_name = 'unique_cache_key'
        _sql_definition = 'UNIQUE(unit_id, start_date, end_date)'
        _message = 'Un cache ne peut exister qu\'une fois par unité et date range'

    @api.model
    def _build_availability_cache(self, unit, start_date, end_date):
        """Build availability cache for a unit and date range"""
        current_date = start_date
        availability_dict = {}
        price_dict = {}
        booking_dict = {}

        while current_date <= end_date:
            date_str = current_date.isoformat()

            # Check if date is booked
            reservations = self.env['onedesk.reservation'].search([
                ('unit_id', '=', unit.id),
                ('start_date', '<=', datetime.combine(current_date, datetime.min.time())),
                ('end_date', '>=', datetime.combine(current_date, datetime.max.time())),
                ('status', 'in', ['pending_payment', 'paid', 'checked_in', 'completed']),
            ])

            if reservations:
                availability_dict[date_str] = 'booked'
                booking_dict[date_str] = [res.name for res in reservations]
            else:
                availability_dict[date_str] = 'available'

            # Get price for this date
            price = unit.get_price_for_dates(current_date, current_date)
            price_dict[date_str] = float(price)

            current_date += timedelta(days=1)

        return {
            'availability': availability_dict,
            'prices': price_dict,
            'bookings': booking_dict,
        }

    @api.model
    def get_availability(self, unit_id, start_date, end_date, use_cache=True):
        """
        Get availability for a unit (fast with cache)
        Returns: {'availability': {...}, 'prices': {...}, 'bookings': {...}}
        """
        unit = self.env['onedesk.unit'].browse(unit_id)
        if not unit:
            return None

        if not use_cache:
            # Build fresh (no cache)
            data = self._build_availability_cache(unit, start_date, end_date)
            return data

        # Try to find existing cache
        cache = self.search([
            ('unit_id', '=', unit_id),
            ('start_date', '=', start_date),
            ('end_date', '=', end_date),
            ('is_valid', '=', True),
            ('expires_at', '>', datetime.now()),
        ], limit=1)

        if cache:
            # Cache HIT!
            cache.cache_hits += 1
            cache.last_accessed = datetime.now()

            try:
                return {
                    'availability': json.loads(cache.availability_data or '{}'),
                    'prices': json.loads(cache.price_data or '{}'),
                    'bookings': json.loads(cache.booking_data or '{}'),
                    'cache': 'HIT',  # Indicate cache was used
                }
            except:
                _logger.warning(f"Cache parse error for unit {unit_id}, rebuilding...")
                cache.is_valid = False
        else:
            # Cache MISS - build fresh
            _logger.info(f"Cache miss for unit {unit_id} ({start_date} to {end_date})")

        # Build fresh cache
        data = self._build_availability_cache(unit, start_date, end_date)

        # Store in cache (24 hour expiry)
        try:
            cache_record = self.create({
                'unit_id': unit_id,
                'start_date': start_date,
                'end_date': end_date,
                'availability_data': json.dumps(data['availability']),
                'price_data': json.dumps(data['prices']),
                'booking_data': json.dumps(data['bookings']),
                'expires_at': datetime.now() + timedelta(hours=24),
            })
            _logger.info(f"✅ Cache created for unit {unit_id}")
        except Exception as e:
            _logger.warning(f"Failed to create cache: {str(e)}")

        # Return with cache miss indicator
        data['cache'] = 'MISS'
        return data

    @api.model
    def invalidate_cache_for_unit(self, unit_id):
        """Invalidate all caches for a unit (called when reservation changes)"""
        caches = self.search([
            ('unit_id', '=', unit_id),
            ('is_valid', '=', True),
        ])

        caches.write({'is_valid': False})
        _logger.info(f"🔄 Invalidated {len(caches)} caches for unit {unit_id}")

    @api.model
    def invalidate_expired_cache(self):
        """Cron: Remove expired cache entries"""
        expired = self.search([
            ('expires_at', '<', datetime.now()),
        ])

        expired.unlink()
        _logger.info(f"🗑️  Cleaned {len(expired)} expired cache entries")

    @api.model
    def cleanup_invalid_cache(self):
        """Cron: Remove invalid cache entries"""
        invalid = self.search([
            ('is_valid', '=', False),
        ])

        invalid.unlink()
        _logger.info(f"🗑️  Cleaned {len(invalid)} invalid cache entries")
