/**
 * Handles sidebar toggle functionality for all screen sizes
 */
function handleSidebarToggle() {
    const sidebarToggle = document.getElementById('sidebarToggle');
    const sidebar = document.querySelector('.sidebar');
    
    if (!sidebarToggle || !sidebar) return;
    
    // Check initial state based on screen size
    function updateSidebarState() {
        if (window.innerWidth < 768) {
            // Mobile view - sidebar should be hidden by default
            document.body.classList.add('sidebar-collapsed');
            sidebar.classList.add('collapsed');
        } else {
            // Desktop view - sidebar should be visible by default
            document.body.classList.remove('sidebar-collapsed');
            sidebar.classList.remove('collapsed');
        }
    }
    
    // Initial state
    updateSidebarState();
    
    // Toggle sidebar when button is clicked
    sidebarToggle.addEventListener('click', function(e) {
        e.preventDefault();
        document.body.classList.toggle('sidebar-collapsed');
        sidebar.classList.toggle('collapsed');
        
        const icon = this.querySelector('i');
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
    
    // Update sidebar state when window is resized
    window.addEventListener('resize', function() {
        updateSidebarState();
    });
    
    // Close sidebar when clicking outside on mobile
    document.addEventListener('click', function(event) {
        if (window.innerWidth < 768) {
            const isOutsideSidebar = !sidebar.contains(event.target);
            const isNotToggleButton = !sidebarToggle.contains(event.target);
            
            if (isOutsideSidebar && isNotToggleButton && !document.body.classList.contains('sidebar-collapsed')) {
                document.body.classList.add('sidebar-collapsed');
                sidebar.classList.add('collapsed');
            }
        }
    });
}

document.addEventListener('DOMContentLoaded', function() {
    handleSidebarToggle();
    
    // Initialize other components
    initializeNavigation();
    initializeComponents();
});

/**
 * Initialize navigation items (active state, etc.)
 */
function initializeNavigation() {
    // Get current URL path
    const currentPath = window.location.pathname;
    
    // Find and activate the current page in the navigation
    const sidebarLinks = document.querySelectorAll('.sidebar .nav-link, .sidebar .collapse-item');
    
    sidebarLinks.forEach(link => {
        const href = link.getAttribute('href');
        
        if (!href || href === '#') return;
        
        if (currentPath === href || (currentPath.startsWith(href) && href !== '/')) {
            link.classList.add('active');
            
            // If in collapse menu, expand that menu
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

/**
 * Initialize other UI components
 */
function initializeComponents() {
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize datepickers
    if (typeof flatpickr !== 'undefined') {
        flatpickr(".datepicker", {
            locale: "vn",
            dateFormat: "Y-m-d",
            allowInput: true
        });

        flatpickr(".datetimepicker", {
            locale: "vn",
            dateFormat: "d/m/Y H:i",
            enableTime: true,
            time_24hr: true,
            allowInput: true
        });
    }

    // Initialize select2 dropdowns
    if (typeof $.fn.select2 !== 'undefined') {
        $('.select2').select2({
            theme: 'bootstrap-5'
        });

        $('.searchable-select').select2({
            theme: 'bootstrap-5',
            allowClear: true
        });
    }
}