CREATE INDEX idx_tickets_status ON tickets (status);
CREATE INDEX idx_tickets_priority ON tickets (priority);
CREATE INDEX idx_tickets_assignee ON tickets (assignee_id);
CREATE INDEX idx_comments_ticket ON comments (ticket_id);
