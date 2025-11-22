# Email Verification Guide - "Vérifier si les emails arrivent bien"

This guide shows you **exactly how to verify** that your automated emails are being sent correctly.

---

## 🎯 Quick Check (2 Minutes)

### 1. Check Email Templates Created
```bash
# In Odoo UI:
Settings → Email → Email Templates
Search: "OneDesk"
Expected: 7 templates listed
```

**New Templates (Phase A)**:
- ✅ OneDesk - Confirmation de réservation
- ✅ OneDesk - Tâche assignée
- ✅ OneDesk - Demande de signature

### 2. Check Email Queue
```bash
# In Odoo UI:
Settings → Email → Sent Emails
Filter: Status = "Waiting to be sent" or "Outgoing"
Expected: See queued emails (if any)
```

### 3. Check Cron Jobs Active
```bash
# In Odoo UI:
Settings → Scheduled Actions
Search: "OneDesk"
Expected: 3 active cron jobs (all have checkmark ✓)
```

---

## 📧 Deep Dive: Email Verification

### Method 1: Check Email Queue (Simplest)
**In Odoo UI**:
1. Settings → Email → Sent Emails
2. Click "Date" column to sort by newest first
3. Look for these patterns:
   - Subject: "Votre réservation est confirmée" → Booking email
   - Subject: "Nouvelle tâche" → Task assignment email
   - Subject: "Signature requise" → Signature request email
   - Subject: "Paiement requis" → Payment reminder email

**What you should see**:
```
Date                Subject                          To              State
2025-11-22 14:30   Votre réservation est confirmée  guest@email.com  Sent ✓
2025-11-22 14:31   📋 Nouvelle tâche: cleaning      staff@email.com  Sent ✓
2025-11-22 14:32   📄 Signature requise: contrat    signer@email.com Sent ✓
```

---

### Method 2: Use Odoo Shell (Developers)

#### A. List All Pending Emails
```python
# In Odoo shell
emails = env['mail.mail'].search([('state', '=', 'outgoing')])
print(f"Pending emails: {len(emails)}")
for email in emails:
    print(f"  {email.create_date}: {email.subject}")
```

**Output**:
```
Pending emails: 3
  2025-11-22 14:30:00: Votre réservation est confirmée
  2025-11-22 14:31:00: 📋 Nouvelle tâche: cleaning
  2025-11-22 14:32:00: 📄 Signature requise: contrat
```

#### B. List All Sent Emails
```python
# In Odoo shell
sent = env['mail.mail'].search([
    ('state', '=', 'sent')
], order='create_date desc', limit=10)

print(f"Recently sent emails ({len(sent)}):")
for email in sent:
    print(f"  ✓ {email.create_date}: {email.subject} → {email.email_to}")
```

**Output**:
```
Recently sent emails (10):
  ✓ 2025-11-22 14:45:00: Votre réservation est confirmée → alice@example.com
  ✓ 2025-11-22 14:46:00: 📋 Nouvelle tâche: cleaning → bob@example.com
  ✓ 2025-11-22 14:47:00: 📄 Signature requise: contrat → charlie@example.com
  ✓ 2025-11-22 14:48:00: 🚨 URGENT: Paiement requis → alice@example.com
  ✓ 2025-11-22 14:49:00: ⚠️ Réservation annulée → alice@example.com
```

#### C. Check Specific Email Type
```python
# Check booking confirmation emails
booking_emails = env['mail.mail'].search([
    ('subject', 'ilike', 'Confirmation de réservation')
], limit=5)

print(f"Booking confirmation emails sent: {len(booking_emails)}")
for email in booking_emails:
    print(f"  ✓ {email.subject}")
    print(f"    To: {email.email_to}")
    print(f"    State: {email.state}")
    print(f"    Date: {email.create_date}\n")
```

**Output**:
```
Booking confirmation emails sent: 3
  ✓ Votre réservation est confirmée - Property ABC 🎉
    To: guest1@example.com
    State: sent
    Date: 2025-11-22 14:30:00

  ✓ Votre réservation est confirmée - Property XYZ 🎉
    To: guest2@example.com
    State: sent
    Date: 2025-11-22 15:15:00
```

#### D. Check Failed Emails
```python
# Check for any failed emails
failed = env['mail.mail'].search([('state', '=', 'failed')])
print(f"Failed emails: {len(failed)}")
for email in failed:
    print(f"  ✗ {email.subject}")
    print(f"    To: {email.email_to}")
    print(f"    Error: {email.failure_reason}\n")
```

#### E. Resend Failed Emails
```python
# Manually send pending emails
pending = env['mail.mail'].search([('state', '=', 'outgoing')])
for email in pending:
    try:
        email.send()
        print(f"✓ Sent: {email.subject}")
    except Exception as e:
        print(f"✗ Failed: {email.subject} - {str(e)}")
```

---

### Method 3: Test Email Delivery (Real Test)

#### Step 1: Create a Test Reservation
```python
# In Odoo shell
test_res = env['onedesk.reservation'].create({
    'name': 'TEST-EMAIL-VERIFY',
    'property_id': env['onedesk.property'].search([], limit=1).id,
    'unit_id': env['onedesk.unit'].search([], limit=1).id,
    'guest_name': 'Test Guest',
    'guest_email': 'your-email@example.com',  # ← Your email!
    'check_in_date': '2025-12-01',
    'check_out_date': '2025-12-08',
    'total_price': 500.0,
    'status': 'pending',
})

print(f"✓ Created test reservation: {test_res.name}")
```

#### Step 2: Trigger Booking Confirmation Email
```python
# Mark as paid to trigger booking email
test_res.status = 'paid'
test_res.save()

print("✓ Triggered booking confirmation email")
```

#### Step 3: Check if Email was Created
```python
# Check email queue
emails = env['mail.mail'].search([
    ('subject', 'ilike', 'Confirmation'),
    ('email_to', 'ilike', 'your-email@example.com')
])

print(f"Found {len(emails)} booking emails")
for email in emails:
    print(f"  ✓ {email.subject}")
    print(f"    State: {email.state}")
```

#### Step 4: Send Email and Check Status
```python
# Send the email
email = emails[0] if emails else None
if email:
    email.send()
    print(f"✓ Email sent!")
    print(f"  Subject: {email.subject}")
    print(f"  State: {email.state}")
    print(f"  Recipient: {email.email_to}")
    print(f"\n📧 Check your inbox at: {email.email_to}")
```

---

## 🧪 Complete Email Workflow Test

### Test Payment Reminder Emails (C1 Phase)
```python
# In Odoo shell

# Step 1: Create test reservation
res = env['onedesk.reservation'].create({
    'name': 'TEST-PAYMENT-FLOW',
    'property_id': env['onedesk.property'].search([], limit=1).id,
    'unit_id': env['onedesk.unit'].search([], limit=1).id,
    'guest_name': 'Payment Test',
    'guest_email': 'test-payment@example.com',  # ← Your email!
    'check_in_date': '2025-12-01',
    'check_out_date': '2025-12-08',
    'total_price': 1000.0,
    'status': 'pending',
})

# Step 2: Create payment retry record (auto-created on reservation)
retry = env['onedesk.payment.retry'].search([
    ('reservation_id', '=', res.id)
])

if not retry:
    retry = env['onedesk.payment.retry'].create({
        'reservation_id': res.id,
    })

print(f"✓ Created payment retry: {retry.id}")

# Step 3: Send Day 1 reminder
retry.action_send_day1_reminder()
print(f"✓ Day 1 reminder sent")
print(f"  Status: {retry.payment_status}")

# Check email was created
emails_day1 = env['mail.mail'].search([
    ('email_to', 'ilike', 'test-payment@example.com'),
    ('subject', 'ilike', 'Paiement'),
], limit=1)
if emails_day1:
    print(f"  Email subject: {emails_day1[0].subject}")
    print(f"  Email state: {emails_day1[0].state}")

# Step 4: Send Day 3 reminder
retry.action_send_day3_reminder()
print(f"✓ Day 3 reminder sent")
print(f"  Status: {retry.payment_status}")

# Check email was created
emails_day3 = env['mail.mail'].search([
    ('email_to', 'ilike', 'test-payment@example.com'),
    ('subject', 'ilike', 'URGENT'),
], limit=1)
if emails_day3:
    print(f"  Email subject: {emails_day3[0].subject}")
    print(f"  Email state: {emails_day3[0].state}")

# Step 5: Check total emails sent
total_emails = env['mail.mail'].search([
    ('email_to', 'ilike', 'test-payment@example.com')
])
print(f"\n✓ Total payment emails created: {len(total_emails)}")
for email in total_emails:
    print(f"  {email.subject}")
```

**Expected Output**:
```
✓ Created payment retry: 42
✓ Day 1 reminder sent
  Status: sent_day1
  Email subject: Rappel de paiement - TEST-PAYMENT-FLOW
  Email state: outgoing
✓ Day 3 reminder sent
  Status: sent_day3
  Email subject: 🚨 URGENT: Paiement requis - TEST-PAYMENT-FLOW
  Email state: outgoing

✓ Total payment emails created: 2
  Rappel de paiement - TEST-PAYMENT-FLOW
  🚨 URGENT: Paiement requis - TEST-PAYMENT-FLOW
```

---

## 📊 Email Statistics Dashboard

### Get Email Summary
```python
# In Odoo shell
from datetime import datetime, timedelta

# Last 24 hours
yesterday = datetime.now() - timedelta(days=1)

# Count by state
sent = env['mail.mail'].search_count([
    ('state', '=', 'sent'),
    ('create_date', '>', yesterday)
])
pending = env['mail.mail'].search_count([
    ('state', '=', 'outgoing'),
    ('create_date', '>', yesterday)
])
failed = env['mail.mail'].search_count([
    ('state', '=', 'failed'),
    ('create_date', '>', yesterday)
])

print("📊 Email Statistics (Last 24 Hours):")
print(f"  ✓ Sent: {sent}")
print(f"  ⏳ Pending: {pending}")
print(f"  ✗ Failed: {failed}")
print(f"  Total: {sent + pending + failed}")

if (sent + pending + failed) > 0:
    success_rate = (sent / (sent + pending + failed)) * 100
    print(f"  Success rate: {success_rate:.1f}%")
```

**Output**:
```
📊 Email Statistics (Last 24 Hours):
  ✓ Sent: 24
  ⏳ Pending: 3
  ✗ Failed: 0
  Total: 27
  Success rate: 88.9%
```

---

## ✅ Verification Checklist

### Basic Verification (5 min)
- [ ] Can navigate to Settings → Email → Email Templates
- [ ] See 7 "OneDesk" templates (3 new + 4 existing)
- [ ] Can navigate to Settings → Email → Sent Emails
- [ ] Can see email list with dates and statuses
- [ ] All 3 "OneDesk" cron jobs are Active

### Advanced Verification (10 min)
- [ ] Run `verify_onedesk_improvements.py` script
- [ ] All Phase A tests pass (email templates)
- [ ] Created test reservation triggers booking email
- [ ] Created payment retry triggers Day 1 reminder email
- [ ] Emails appear in mail queue

### Production Verification (1 hour)
- [ ] Monitor email delivery for 1 hour
- [ ] Check success rate > 90%
- [ ] Verify no failed emails
- [ ] Check actual email inbox (if configured)
- [ ] Monitor Odoo logs for email errors

---

## 🆘 Troubleshooting

### Problem: No emails in queue
**Solution**:
```python
# Check if mail server is configured
config = env['ir.config_parameter'].sudo()
smtp_server = config.get_param('mail.smtp.server')
print(f"SMTP Server: {smtp_server}")

if not smtp_server:
    print("⚠️ No SMTP configured!")
    print("   Go to: Settings → Email → Outgoing Mail Servers")
```

### Problem: Emails stuck in "outgoing" state
**Solution**:
```python
# Try sending manually
stuck = env['mail.mail'].search([('state', '=', 'outgoing')], limit=1)
if stuck:
    stuck.send()
    print(f"Email state: {stuck.state}")
```

### Problem: Email templates not creating emails
**Solution**:
```python
# Verify template exists
template = env.ref('onedesk_core.email_template_booking_confirmation')
print(f"Template: {template.name}")
print(f"Model: {template.model_id}")

# Try sending manually
if template:
    template.send_mail(res.id, force_send=True)
    print("✓ Email sent via template")
```

---

## 📈 Monitoring Email Delivery

### Daily Check
```python
# Add this to your monitoring routine
from datetime import datetime, timedelta

today = datetime.now().date()
today_emails = env['mail.mail'].search([
    ('create_date', '>=', str(today)),
])

sent = len([e for e in today_emails if e.state == 'sent'])
pending = len([e for e in today_emails if e.state == 'outgoing'])
failed = len([e for e in today_emails if e.state == 'failed'])

print(f"📧 Today's Email Activity ({today}):")
print(f"   Sent: {sent}")
print(f"   Pending: {pending}")
print(f"   Failed: {failed}")
```

### Weekly Report
```python
# Generate weekly email report
from datetime import datetime, timedelta

week_ago = datetime.now() - timedelta(days=7)
week_emails = env['mail.mail'].search([
    ('create_date', '>=', week_ago)
])

by_type = {}
for email in week_emails:
    subject = email.subject.split(' - ')[0] if ' - ' in email.subject else email.subject[:30]
    by_type[subject] = by_type.get(subject, 0) + 1

print("📊 Email Report (Last 7 Days):")
for subject, count in sorted(by_type.items(), key=lambda x: x[1], reverse=True):
    print(f"  {subject}: {count}")
```

---

## 🎯 Success Criteria

✅ All emails created successfully:
  - Booking confirmation on reservation paid
  - Task assignment on task creation
  - Signature request on signer added

✅ Email queue shows emails:
  - Settings → Email → Sent Emails shows records
  - States are "sent" or "outgoing"
  - No "failed" state

✅ Payment reminders working:
  - Day 1 reminder triggers 1 day after pending
  - Day 3 reminder triggers 3 days after pending
  - Auto-cancel triggers 7 days after pending

✅ Performance metrics:
  - Email delivery > 95%
  - No errors in Odoo logs
  - Response time < 500ms for template rendering

---

**Happy email testing!** 📧

If you're not seeing emails, check `QUICK_START.md` → Troubleshooting section
