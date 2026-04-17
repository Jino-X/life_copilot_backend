-- Test Emails for Development
-- Run this SQL to add sample emails to your database for testing

-- First, get your user ID (replace with your actual user ID)
-- You can find it by running: SELECT id, email FROM users;

-- Insert test emails (UPDATE user_id=1 to your actual user ID)
INSERT INTO emails (
    user_id, 
    gmail_id, 
    subject, 
    sender, 
    snippet, 
    summary, 
    category, 
    is_read, 
    is_starred, 
    is_archived, 
    received_at, 
    synced_at
) VALUES 
-- Unread important work email
(
    1,  -- UPDATE THIS to your user ID
    'test-email-001',
    'Q4 Project Deadline Approaching',
    'Sarah Johnson <sarah.j@company.com>',
    'Hi team, just a reminder that our Q4 project deadline is next Friday. Please ensure all deliverables are ready for review by Wednesday...',
    'Reminder about Q4 project deadline next Friday. All deliverables need to be ready for review by Wednesday.',
    'work',
    false,  -- unread
    true,   -- starred
    false,  -- not archived
    NOW() - INTERVAL '2 hours',
    NOW()
),

-- Unread personal email
(
    1,  -- UPDATE THIS to your user ID
    'test-email-002',
    'Dinner plans this weekend?',
    'Alex Chen <alex.chen@email.com>',
    'Hey! Hope you''re doing well. I was thinking we could grab dinner this weekend. Are you free Saturday evening? Let me know!',
    'Friend asking about dinner plans for Saturday evening this weekend.',
    'personal',
    false,  -- unread
    false,
    false,
    NOW() - INTERVAL '4 hours',
    NOW()
),

-- Read newsletter
(
    1,  -- UPDATE THIS to your user ID
    'test-email-003',
    'Your Weekly Tech Digest - AI Breakthroughs',
    'TechNews Weekly <newsletter@technews.com>',
    'This week in tech: Major AI breakthroughs, new smartphone releases, and the latest in cloud computing. Plus exclusive interviews with industry leaders...',
    'Weekly tech newsletter covering AI breakthroughs, smartphone releases, cloud computing updates, and industry leader interviews.',
    'newsletter',
    true,   -- read
    false,
    false,
    NOW() - INTERVAL '1 day',
    NOW()
),

-- Unread important email with high priority
(
    1,  -- UPDATE THIS to your user ID
    'test-email-004',
    'URGENT: Security Update Required',
    'IT Security <security@company.com>',
    'Action Required: A critical security update needs to be installed on your workstation by end of day. Please click the link below to schedule the update...',
    'Urgent security update required on workstation by end of day. Action needed.',
    'important',
    false,  -- unread
    true,   -- starred
    false,
    NOW() - INTERVAL '30 minutes',
    NOW()
),

-- Read follow-up email
(
    1,  -- UPDATE THIS to your user ID
    'test-email-005',
    'Re: Meeting Notes from Yesterday',
    'Michael Brown <m.brown@company.com>',
    'Thanks for the meeting yesterday. I''ve attached the notes we discussed. Could you review the action items and let me know if I missed anything?',
    'Follow-up from yesterday''s meeting with attached notes. Requesting review of action items.',
    'follow_up',
    true,   -- read
    false,
    false,
    NOW() - INTERVAL '1 day',
    NOW()
),

-- Archived newsletter
(
    1,  -- UPDATE THIS to your user ID
    'test-email-006',
    'Special Offer: 50% Off Premium Subscription',
    'Deals & Offers <offers@service.com>',
    'Limited time offer! Get 50% off our premium subscription for the next 48 hours. Upgrade now to unlock all features and enjoy unlimited access...',
    'Limited time 50% discount offer on premium subscription for next 48 hours.',
    'newsletter',
    true,   -- read
    false,
    true,   -- archived
    NOW() - INTERVAL '3 days',
    NOW()
),

-- Unread work email
(
    1,  -- UPDATE THIS to your user ID
    'test-email-007',
    'Team Standup - Tomorrow 10 AM',
    'Project Manager <pm@company.com>',
    'Reminder: Our weekly team standup is scheduled for tomorrow at 10 AM. Please come prepared with your updates and any blockers you''re facing.',
    'Weekly team standup reminder for tomorrow 10 AM. Come prepared with updates and blockers.',
    'work',
    false,  -- unread
    false,
    false,
    NOW() - INTERVAL '6 hours',
    NOW()
),

-- Read personal email with AI summary
(
    1,  -- UPDATE THIS to your user ID
    'test-email-008',
    'Photos from our trip!',
    'Emma Wilson <emma.w@email.com>',
    'Hi! I finally got around to organizing the photos from our trip last month. I''ve uploaded them to a shared album. Check them out when you get a chance!',
    'Friend sharing organized photos from last month''s trip in a shared album.',
    'personal',
    true,   -- read
    false,
    false,
    NOW() - INTERVAL '2 days',
    NOW()
);

-- Verify the emails were inserted
SELECT 
    id,
    subject,
    sender,
    category,
    is_read,
    is_starred,
    is_archived,
    received_at
FROM emails
WHERE user_id = 1  -- UPDATE THIS to your user ID
ORDER BY received_at DESC;
