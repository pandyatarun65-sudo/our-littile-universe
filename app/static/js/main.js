document.addEventListener('DOMContentLoaded', () => {
    const fadeItems = document.querySelectorAll('.timeline-row, .gallery-item, .stat-card');
    fadeItems.forEach((item, index) => {
        item.style.animationDelay = `${index * 70}ms`;
    });

    const navToggle = document.getElementById('navToggle');
    const mainNav = document.getElementById('mainNav');
    if (navToggle && mainNav) {
        navToggle.addEventListener('click', () => {
            const isOpen = mainNav.classList.toggle('is-open');
            navToggle.classList.toggle('is-active', isOpen);
            navToggle.setAttribute('aria-expanded', isOpen);
        });
    }

    const photoInput = document.getElementById('photo');
    const uploadPreview = document.getElementById('uploadPreview');
    const placeholderText = document.getElementById('uploadPlaceholderText');
    if (photoInput && uploadPreview) {
        photoInput.addEventListener('change', () => {
            const file = photoInput.files[0];
            if (!file) return;
            const reader = new FileReader();
            reader.onload = (event) => {
                uploadPreview.style.backgroundImage = `url(${event.target.result})`;
                if (placeholderText) placeholderText.hidden = true;
            };
            reader.readAsDataURL(file);
        });
    }

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