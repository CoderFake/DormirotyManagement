function handleSidebarToggle() {
    const sidebarToggle = document.getElementById('sidebarToggle');
    const sidebar = document.querySelector('.sidebar');

    if (!sidebarToggle || !sidebar) return;

    function updateSidebarState() {
        if (window.innerWidth < 768) {
            document.body.classList.add('sidebar-collapsed');
            sidebar.classList.add('collapsed');
            sidebar.classList.remove('show');

            const icon = sidebarToggle.querySelector('i');
            if (icon) {
                icon.classList.remove('fa-times');
                icon.classList.add('fa-bars');
            }
        } else {
            document.body.classList.remove('sidebar-collapsed');
            sidebar.classList.remove('collapsed');

            const icon = sidebarToggle.querySelector('i');
            if (icon) {
                icon.classList.remove('fa-times');
                icon.classList.add('fa-bars');
            }
        }
    }

    updateSidebarState();

    sidebarToggle.addEventListener('click', function(e) {
        e.preventDefault();

        if (window.innerWidth < 768) {
            sidebar.classList.toggle('show');
            sidebar.classList.remove('collapsed');

            if (sidebar.classList.contains('show')) {
                let overlay = document.querySelector('.sidebar-overlay');
                if (!overlay) {
                    overlay = document.createElement('div');
                    overlay.className = 'sidebar-overlay';
                    document.body.appendChild(overlay);

                    overlay.addEventListener('click', function() {
                        sidebar.classList.remove('show');
                        overlay.remove();

                        const icon = sidebarToggle.querySelector('i');
                        if (icon) {
                            icon.classList.remove('fa-times');
                            icon.classList.add('fa-bars');
                            sidebarToggle.classList.add('rotate-right');
                            sidebarToggle.classList.remove('rotate-left');
                        }
                    });
                }
            } else {
                const overlay = document.querySelector('.sidebar-overlay');
                if (overlay) {
                    overlay.remove();
                }
            }
        } else {
            document.body.classList.toggle('sidebar-collapsed');
            sidebar.classList.toggle('collapsed');
        }

        const icon = this.querySelector('i');
        if (icon) {
            if (icon.classList.contains('fa-bars')) {
                icon.classList.remove('fa-bars');
                icon.classList.add('fa-times');
                sidebarToggle.classList.add('rotate-left');
                sidebarToggle.classList.remove('rotate-right');
            } else {
                icon.classList.remove('fa-times');
                icon.classList.add('fa-bars');
                sidebarToggle.classList.add('rotate-right');
                sidebarToggle.classList.remove('rotate-left');
            }
        }
    });

    window.addEventListener('resize', function() {
        if (window.innerWidth >= 768) {
            const overlay = document.querySelector('.sidebar-overlay');
            if (overlay) {
                overlay.remove();
            }
        }

        updateSidebarState();
    });

    document.addEventListener('click', function(event) {
        if (window.innerWidth < 768) {
            const isOutsideSidebar = !sidebar.contains(event.target);
            const isNotToggleButton = !sidebarToggle.contains(event.target);

            if (isOutsideSidebar && isNotToggleButton && sidebar.classList.contains('show')) {
                sidebar.classList.remove('show');

                const overlay = document.querySelector('.sidebar-overlay');
                if (overlay) {
                    overlay.remove();
                }

                const icon = sidebarToggle.querySelector('i');
                if (icon) {
                    icon.classList.remove('fa-times');
                    icon.classList.add('fa-bars');
                    sidebarToggle.classList.add('rotate-right');
                    sidebarToggle.classList.remove('rotate-left');
                }
            }
        }
    });
}

document.addEventListener('DOMContentLoaded', function() {
    handleSidebarToggle();

    initializeNavigation();
    initializeComponents();

    const alerts = document.querySelectorAll('.alert-auto-close');
    alerts.forEach(alert => {
        alert.classList.remove('d-none');
    });
});

function initializeNavigation() {
    const currentPath = window.location.pathname;

    const sidebarLinks = document.querySelectorAll('.sidebar .nav-link, .sidebar .collapse-item');

    sidebarLinks.forEach(link => {
        const href = link.getAttribute('href');

        if (!href || href === '#') return;

        if (currentPath === href || (currentPath.startsWith(href) && href !== '/')) {
            link.classList.add('active');

            const collapseMenu = link.closest('.collapse');
            if (collapseMenu) {
                collapseMenu.classList.add('show');
                const parentLink = document.querySelector(`[data-bs-toggle="collapse"][data-bs-target="#${collapseMenu.id}"]`);
                if (parentLink) {
                    parentLink.classList.add('active');
                    parentLink.setAttribute('aria-expanded', 'true');
                }
            }
        }
    });
}

function initializeComponents() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    if (typeof flatpickr !== 'undefined') {
        flatpickr(".datepicker", {
            locale: "vn",
            dateFormat: "Y-m-d",
            allowInput: true
        });

        flatpickr(".datetimepicker", {
            locale: "vn",
            dateFormat: "Y-m-d H:i",
            enableTime: true,
            time_24hr: true,
            allowInput: true
        });
    }

    if (typeof $.fn.select2 !== 'undefined') {
        $('.select2').select2({
            theme: 'bootstrap-5'
        });

        $('.searchable-select').select2({
            theme: 'bootstrap-5',
            allowClear: true
        });
    }

    function updateNotificationCount() {
        fetch('/notification/api/unread-count/')
            .then(response => response.json())
            .then(data => {
                const badgeElement = document.querySelector('#alertsDropdown .badge');
                if (badgeElement) {
                    if (data.count > 0) {
                        badgeElement.textContent = data.count;
                        badgeElement.classList.remove('d-none');
                    } else {
                        badgeElement.classList.add('d-none');
                    }
                }
            })
            .catch(error => console.error('Error fetching notification count:', error));
    }

    if (document.querySelector('#alertsDropdown')) {
        updateNotificationCount();

        setInterval(updateNotificationCount, 60000);
    }
}