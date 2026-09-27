// Adds a small staggered delay to elements that fade in, so cards/timeline
// items appear one after another instead of all at once. Purely cosmetic —
// the page works fine even if JS is disabled.

document.addEventListener('DOMContentLoaded', () => {
    const fadeItems = document.querySelectorAll('.memory-card, .timeline-item');

    fadeItems.forEach((item, index) => {
        item.style.animationDelay = `${index * 80}ms`;
    });
});
