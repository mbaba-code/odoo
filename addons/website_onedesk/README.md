# OneDesk Website Module

Public-facing website for OneDesk property listings and booking requests.

## Overview

This module creates a professional property rental website integrated with OneDesk's core reservation system. It allows customers to:

- Browse all available properties
- View detailed property information and amenities
- Check unit availability for specific dates
- See pricing in real-time
- Submit booking requests

## Installation

1. Place the `website_onedesk` folder in your Odoo addons directory
2. Install module dependencies:
   - onedesk_core
   - website

3. Go to **Apps** → Search "OneDesk Website" → Install

## Features

### Public Pages

#### 1. Property Listing (`/properties`)
- Display all properties as cards
- Show property type, address, number of units
- Display monthly revenue and occupancy rate
- Click to view property details

#### 2. Property Detail (`/property/<id>`)
- Full property information and description
- List of amenities/equipment
- Cards for each available unit
- Unit pricing and specifications
- Contact information

#### 3. Unit Booking (`/unit/<id>`)
- Interactive date picker
- Real-time availability checking
- Instant price calculation (with cleaning fees)
- Booking request form with:
  - Guest name, email, phone
  - Arrival/departure dates
  - Special requests field
- Responsive design for mobile and desktop

### AJAX Endpoints

#### Check Availability
```
POST /unit/<unit_id>/availability
{
  "start_date": "2024-12-20",
  "end_date": "2024-12-25"
}

Response:
{
  "available": true,
  "nights": 5,
  "price_per_night": 150.00,
  "total_price": 750.00,
  "cleaning_fee": 50.00,
  "total_with_cleaning": 800.00
}
```

#### Create Booking Request
```
POST /property/booking
{
  "unit_id": 123,
  "name": "John Doe",
  "email": "john@example.com",
  "phone": "+33612345678",
  "start_date": "2024-12-20",
  "end_date": "2024-12-25",
  "message": "Need a crib for baby"
}

Response:
{
  "status": "success",
  "message": "Demande de réservation créée! ID: 456",
  "reservation_id": 456
}
```

## Configuration

### URL Structure

- Home: `/properties`
- Property detail: `/property/123` (where 123 is property_id)
- Unit booking: `/unit/456` (where 456 is unit_id)

### Customization

#### Change Colors
Edit `static/css/website_onedesk.css`:

```css
:root {
    --primary-color: #667eea;      /* Main purple */
    --secondary-color: #764ba2;    /* Dark purple */
    --success-color: #48c774;      /* Green */
    --danger-color: #f14668;       /* Red */
}
```

#### Add Logo
Replace `/static/images/logo.png` and update the template in `templates/pages.xml`.

#### Custom Domain
Configure your Odoo website domain in **Settings** → **Website** → **Domain**.

## How Bookings Work

1. **Customer submits booking request** on `/unit/<id>`
   - Form creates a draft reservation in the system
   - Email sent to customer confirming receipt

2. **Property manager reviews** in OneDesk backend
   - Goes to **Reservations** menu
   - Opens draft reservation
   - Manually confirms or rejects

3. **Once confirmed**, customer receives:
   - Confirmation email
   - Payment link
   - Check-in instructions (24h before arrival)

## Backend Integration

### Relevant Models
- `onedesk.property` - Properties
- `onedesk.unit` - Rental units/rooms
- `onedesk.reservation` - Bookings
- `onedesk.seasonal_price` - Seasonal pricing

### Relevant Fields Used
- Property: name, address, property_type, amenities, description, owner_*
- Unit: name, bedrooms, bathrooms, capacity, price_per_night, cleaning_fee, cleaning_duration_hours, cancellation_policy, minimum_stay, maintenance_notes
- Reservation: status, partner_id, start_date, end_date, guest_notes, special_requests

## Frontend Pages

### Property List Template
**File**: `templates/pages.xml` → `template id="properties_list"`

Shows all properties as responsive grid of cards with:
- Type badge
- Address
- Number of units
- Monthly revenue
- Occupancy percentage
- Link to property detail

### Property Detail Template
**File**: `templates/pages.xml` → `template id="property_detail"`

Shows property information and lists available units.

### Unit Detail & Booking
**File**: `templates/pages.xml` → `template id="unit_detail"`

Interactive booking page with:
- Unit specifications
- Date picker
- Live price calculation
- Booking form
- Availability checking via AJAX

## Styling & Assets

### CSS File
- Location: `static/css/website_onedesk.css`
- Framework: Bootstrap 5 (from website.layout)
- Design: Modern, responsive, professional

### Included Features
- Gradient backgrounds
- Smooth animations and transitions
- Hover effects on cards
- Mobile-responsive grid
- Form styling
- Badge and alert styling

## Development

### Adding a New Page

1. Add route to `controllers/main.py`:
```python
@http.route('/my-page', type='http', auth='public', website=True)
def my_page(self, **kw):
    return request.render('website_onedesk.my_page_template', {
        'my_data': 'value',
    })
```

2. Add template to `templates/pages.xml`:
```xml
<template id="my_page_template" name="My Page">
    <t t-call="website.layout">
        <!-- Your content here -->
    </t>
</template>
```

### Modifying Templates
All templates inherit from `website.layout` which provides:
- Navigation bar
- Footer
- Bootstrap 5 grid system
- CSRF token for forms

## Security Notes

- All routes default to `auth='public'` (no login required)
- CSRF tokens automatically handled by Odoo
- Form validation on backend
- Email validation on frontend and backend
- No sensitive data exposed in frontend

## Performance

- Properties cached by Odoo ORM
- AJAX endpoints optimized for real-time queries
- CSS is minified in production
- No heavy JavaScript libraries required

## Troubleshooting

### Pages not showing
1. Check module is installed: **Apps** → search "OneDesk Website"
2. Check website is enabled: **Website** → **Website**
3. Check URL: should start with `/properties`

### Booking requests not created
1. Check customer email is valid
2. Check unit and dates are provided
3. Check backend logs: `journalctl -u odoo`

### Emails not sending
1. Configure SMTP: **Settings** → **Technical** → **Email Configuration**
2. Check email is in correct format
3. Check mail queue: **Discuss** → **Emails**

## Future Enhancements

Possible improvements (not yet implemented):

- [ ] Guest reviews/ratings system
- [ ] Multiple language support
- [ ] Photo galleries for units
- [ ] Virtual tours
- [ ] Instant payment integration
- [ ] SMS notifications
- [ ] Customer portal (view bookings)
- [ ] Admin dashboard
- [ ] SEO optimization
- [ ] Google Analytics integration

## Support

For issues or feature requests, contact the development team.
