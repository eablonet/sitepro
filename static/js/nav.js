document.addEventListener('DOMContentLoaded', function () {
    var burgerToggle = document.getElementById('burger-toggle');
    var mobileNav = document.getElementById('mobile-nav');

    if (burgerToggle && mobileNav) {
        burgerToggle.addEventListener('click', function () {
            var isOpen = !mobileNav.hidden;
            mobileNav.hidden = isOpen;
            burgerToggle.setAttribute('aria-expanded', String(!isOpen));

            var icon = burgerToggle.querySelector('i');
            icon.classList.toggle('ti-menu-2', isOpen);
            icon.classList.toggle('ti-x', !isOpen);
        });
    }

    var accordionTriggers = document.querySelectorAll('.mobile-nav__accordion-trigger');
    accordionTriggers.forEach(function (trigger) {
        var panel = document.getElementById(trigger.getAttribute('aria-controls'));
        if (!panel) return;

        trigger.addEventListener('click', function () {
            var isOpen = !panel.hidden;
            panel.hidden = isOpen;
            trigger.setAttribute('aria-expanded', String(!isOpen));
            trigger.classList.toggle('mobile-nav__accordion-trigger--open', !isOpen);
        });
    });
});