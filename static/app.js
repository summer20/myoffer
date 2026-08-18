// MyOffer — small vanilla-JS interaction layer (no build step, no dependencies).
// Three behaviors: number count-up, scroll-reveal, and an HTMX loading shimmer.

const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

function animateCount(el) {
    const target = parseInt(el.dataset.countTo, 10) || 0;
    if (prefersReducedMotion) {
        el.textContent = target;
        return;
    }
    const duration = 700;
    const start = performance.now();
    function step(now) {
        const progress = Math.min((now - start) / duration, 1);
        const eased = 1 - Math.pow(1 - progress, 3);
        el.textContent = Math.round(eased * target);
        if (progress < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
}

const revealObserver = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
        if (entry.isIntersecting) {
            entry.target.classList.add("is-visible");
            revealObserver.unobserve(entry.target);
        }
    });
}, { threshold: 0.1 });

function observeReveals(root) {
    root.querySelectorAll(".reveal:not(.is-visible)").forEach((el) => revealObserver.observe(el));
}

document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("[data-count-to]").forEach(animateCount);
    observeReveals(document);
});

// New rows/cards/stats inserted by HTMX swaps need to be picked up too, or
// reveal-cards would stay permanently invisible and stat numbers would stay
// frozen at "0" instead of animating in.
document.body.addEventListener("htmx:afterSwap", (e) => {
    observeReveals(e.detail.target);
    e.detail.target.querySelectorAll("[data-count-to]").forEach(animateCount);
});

// Loading shimmer: htmx only auto-tags the *triggering* element with
// htmx-request, not the swap target. Listening on beforeRequest/afterRequest
// and tagging event.detail.target directly works for every hx-target in the
// app without per-element hx-indicator wiring.
document.body.addEventListener("htmx:beforeRequest", (e) => {
    if (e.detail.target) e.detail.target.classList.add("is-loading");
});
document.body.addEventListener("htmx:afterRequest", (e) => {
    if (e.detail.target) e.detail.target.classList.remove("is-loading");
});
