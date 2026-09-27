document.addEventListener('DOMContentLoaded', () => {
    const fadeItems = document.querySelectorAll('.memory-card, .timeline-item, .gallery-item');

    fadeItems.forEach((item, index) => {
        item.style.animationDelay = `${index * 80}ms`;
    });

    const lightbox = document.getElementById('lightbox');
    if (!lightbox) return;

    const lightboxImage = document.getElementById('lightbox-image');
    const lightboxCaption = document.getElementById('lightbox-caption');
    const closeButton = document.getElementById('lightbox-close');

    function openLightbox(src, caption) {
        lightboxImage.src = src;
        lightboxCaption.textContent = caption || '';
        lightbox.hidden = false;
    }

    function closeLightbox() {
        lightbox.hidden = true;
        lightboxImage.src = '';
    }

    document.querySelectorAll('.gallery-item').forEach((item) => {
        item.addEventListener('click', () => {
            openLightbox(item.dataset.src, item.dataset.caption);
        });
    });

    closeButton.addEventListener('click', closeLightbox);
    lightbox.addEventListener('click', (event) => {
        if (event.target === lightbox) closeLightbox();
    });
    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape') closeLightbox();
    });
});