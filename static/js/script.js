/**
 * Main JavaScript file for Dormitory Management System
 */

document.addEventListener('DOMContentLoaded', function () {
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // Auto-close alerts
    setTimeout(function () {
        const alerts = document.querySelectorAll('.alert-auto-close');
        alerts.forEach(function (alert) {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 5000);


    // Handle sidebar active state
    handleSidebarActiveState();

    // Handle sidebar toggle
    handleSidebarToggle();

    // Initialize Flatpickr datepickers
    initializeFlatpickr();

    // Initialize Select2 if present
    initializeSelect2();
});

/**
 * Handles sidebar active state
 */
function handleSidebarActiveState() {
    // Get current URL path
    const currentPath = window.location.pathname;

    // Find and mark active sidebar items
    const sidebarLinks = document.querySelectorAll('.sidebar .nav-link, .sidebar .collapse-item');

    sidebarLinks.forEach(link => {
        const href = link.getAttribute('href');

        // Skip empty hrefs or # links
        if (!href || href === '#') return;

        // Check if the current path matches or starts with the link href (except for root path)
        if (currentPath === href || (currentPath.startsWith(href) && href !== '/')) {
            // Mark the link as active
            link.classList.add('active');

            // If it's inside a collapse menu, expand that menu
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

    // Store active link when clicking
    sidebarLinks.forEach(link => {
        link.addEventListener('click', function () {
            // Skip if this is a toggle or # link
            if (this.getAttribute('data-bs-toggle') || this.getAttribute('href') === '#') return;

            // Store this link as the active one in localStorage
            localStorage.setItem('activeLink', this.getAttribute('href'));
        });
    });

    // Also check for previously active link in localStorage
    const storedActiveLink = localStorage.getItem('activeLink');
    if (storedActiveLink) {
        const matchingLink = document.querySelector(`.sidebar a[href="${storedActiveLink}"]`);
        if (matchingLink && !matchingLink.classList.contains('active')) {
            matchingLink.classList.add('active');

            // If it's inside a collapse menu, expand that menu
            const collapseMenu = matchingLink.closest('.collapse');
            if (collapseMenu) {
                collapseMenu.classList.add('show');
                const parentLink = document.querySelector(`[data-bs-toggle="collapse"][data-bs-target="#${collapseMenu.id}"]`);
                if (parentLink) {
                    parentLink.classList.add('active');
                    parentLink.setAttribute('aria-expanded', 'true');
                }
            }
        }
    }
}

/**
 * Handles sidebar toggle functionality
 */
function handleSidebarToggle() {
    const sidebarToggle = document.getElementById('sidebarToggle');
    if (sidebarToggle) {
        // Check for stored state
        const sidebarState = localStorage.getItem('sidebarToggled');
        if (sidebarState === 'true') {
            document.body.classList.add('sidebar-toggled');
            document.querySelector('.sidebar').classList.add('toggled');
        }

        sidebarToggle.addEventListener('click', function (e) {
            e.preventDefault();
            document.body.classList.toggle('sidebar-toggled');
            const sidebar = document.querySelector('.sidebar');
            sidebar.classList.toggle('toggled');

            // Store state in localStorage
            localStorage.setItem('sidebarToggled', sidebar.classList.contains('toggled'));
        });
    }

    // Close any open menu when window is resized below 992px
    window.addEventListener('resize', function () {
        if (window.innerWidth < 992) {
            document.querySelectorAll('.sidebar .collapse.show').forEach(el => {
                const bsCollapse = new bootstrap.Collapse(el);
                bsCollapse.hide();
            });
        }
    });
}

/**
 * Initialize Flatpickr datepickers
 */
function initializeFlatpickr() {
    if (typeof flatpickr !== 'undefined') {
        // Regular date pickers
        flatpickr(".datepicker", {
            locale: "vn",
            dateFormat: "Y-m-d",
            allowInput: true
        });

        // Date-time pickers
        flatpickr(".datetimepicker", {
            locale: "vn",
            dateFormat: "d/m/Y H:i",
            enableTime: true,
            time_24hr: true,
            allowInput: true
        });
    }
}

/**
 * Initialize Select2 dropdowns
 */
function initializeSelect2() {
    if (typeof $.fn.select2 !== 'undefined') {
        $('.select2').select2({
            theme: 'bootstrap-5'
        });

        // For searchable selects
        $('.searchable-select').select2({
            theme: 'bootstrap-5',
            allowClear: true
        });
    }
}

/**
 * Show loading spinner
 */
function showLoading() {
    const loadingEl = document.createElement('div');
    loadingEl.className = 'loading-overlay';
    loadingEl.innerHTML = `
        <div class="spinner-border text-primary" role="status">
            <span class="visually-hidden">Loading...</span>
        </div>
    `;
    document.body.appendChild(loadingEl);
    document.body.classList.add('loading');
}

/**
 * Hide loading spinner
 */
function hideLoading() {
    const loadingEl = document.querySelector('.loading-overlay');
    if (loadingEl) {
        loadingEl.remove();
        document.body.classList.remove('loading');
    }
}

/**
 * Format currency (VND)
 */
function formatCurrency(amount) {
    return new Intl.NumberFormat('vi-VN', {style: 'currency', currency: 'VND'}).format(amount);
}

/**
 * Format date in Vietnamese format
 */
function formatDate(dateString) {
    const date = new Date(dateString);
    return new Intl.DateTimeFormat('vi-VN', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric'
    }).format(date);
}

/**
 * Format datetime in Vietnamese format
 */
function formatDateTime(dateString) {
    const date = new Date(dateString);
    return new Intl.DateTimeFormat('vi-VN', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    }).format(date);
}

/**
 * Handle form confirmation
 */
function confirmAction(message, callback) {
    if (confirm(message)) {
        callback();
    }
}

/**
 * Copy text to clipboard
 */
function copyToClipboard(text) {
    const tempInput = document.createElement('input');
    tempInput.value = text;
    document.body.appendChild(tempInput);
    tempInput.select();
    document.execCommand('copy');
    document.body.removeChild(tempInput);

    // Show toast notification
    if (typeof toastr !== 'undefined') {
        toastr.success('Đã sao chép vào clipboard!');
    }
}


/**
 * Mobile sidebar functionality
 */
function initMobileSidebar() {
    const sidebarToggle = document.getElementById('sidebarToggle');
    const sidebar = document.querySelector('.sidebar');

    // Function to handle sidebar toggle
    function toggleSidebar() {
        document.body.classList.toggle('sidebar-toggled');
        sidebar.classList.toggle('show');
    }

    // Add click event to sidebar toggle button
    if (sidebarToggle) {
        sidebarToggle.addEventListener('click', function (e) {
            e.preventDefault();
            toggleSidebar();
        });
    }

    // Close sidebar when clicking outside on mobile
    document.addEventListener('click', function (event) {
        const windowWidth = window.innerWidth;
        if (windowWidth < 992) {
            const isOutsideSidebar = !sidebar.contains(event.target);
            const isNotToggleButton = !sidebarToggle.contains(event.target);

            if (isOutsideSidebar && isNotToggleButton && document.body.classList.contains('sidebar-toggled')) {
                toggleSidebar();
            }
        }
    });

    // Close sidebar when window resizes past breakpoint
    window.addEventListener('resize', function () {
        if (window.innerWidth >= 992 && document.body.classList.contains('sidebar-toggled')) {
            document.body.classList.remove('sidebar-toggled');
            sidebar.classList.remove('show');
        }
    });

    const sidebarLinks = document.querySelectorAll('.sidebar .nav-link, .sidebar .collapse-item');
    sidebarLinks.forEach(link => {
        if (!link.getAttribute('data-bs-toggle')) {
            link.addEventListener('click', function () {
                if (window.innerWidth < 992) {
                    setTimeout(() => {
                        document.body.classList.remove('sidebar-toggled');
                        sidebar.classList.remove('show');
                    }, 150);
                }
            });
        }
    });
}

document.addEventListener('DOMContentLoaded', function () {
    initMobileSidebar();
});

document.addEventListener('DOMContentLoaded', function() {
    const sidebarToggle = document.getElementById('sidebarToggle');

    if (sidebarToggle) {
        sidebarToggle.addEventListener('click', function(e) {
            e.preventDefault();
            document.body.classList.toggle('sidebar-toggled');
            document.querySelector('.sidebar').classList.toggle('toggled');

            const icon = sidebarToggle.querySelector('i');
            if (icon) {
                if (icon.classList.contains('fa-chevron-left')) {
                    icon.classList.remove('fa-chevron-left');
                    icon.classList.add('fa-chevron-right');
                } else {
                    icon.classList.remove('fa-chevron-right');
                    icon.classList.add('fa-chevron-left');
                }
            }
        });
    }
});