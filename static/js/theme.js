/**
 * LMS Platform - Theme System
 * Dark/Light mode toggle with localStorage persistence
 */

(function() {
  'use strict';

  // Theme constants
  const THEME_KEY = 'lms-theme';
  const DARK_THEME = 'dark';
  const LIGHT_THEME = 'light';

  /**
   * Get the current theme from localStorage or system preference
   */
  function getStoredTheme() {
    return localStorage.getItem(THEME_KEY);
  }

  /**
   * Get system preferred theme
   */
  function getPreferredTheme() {
    const storedTheme = getStoredTheme();
    if (storedTheme) {
      return storedTheme;
    }
    return window.matchMedia('(prefers-color-scheme: light)').matches ? LIGHT_THEME : DARK_THEME;
  }

  /**
   * Set theme on the document
   */
  function setTheme(theme) {
    const htmlEl = document.documentElement;

    // Set both attributes for compatibility
    htmlEl.setAttribute('data-bs-theme', theme);
    htmlEl.setAttribute('data-theme', theme);

    // Update localStorage
    localStorage.setItem(THEME_KEY, theme);

    // Update toggle button icon
    updateToggleIcon(theme);

    // Dispatch custom event
    window.dispatchEvent(new CustomEvent('themechange', { detail: { theme } }));
  }

  /**
   * Update toggle button icon based on current theme
   */
  function updateToggleIcon(theme) {
    const toggleBtns = document.querySelectorAll('.theme-toggle');
    toggleBtns.forEach(btn => {
      const sunIcon = btn.querySelector('.bi-sun');
      const moonIcon = btn.querySelector('.bi-moon-stars');

      if (sunIcon && moonIcon) {
        if (theme === LIGHT_THEME) {
          sunIcon.style.display = 'inline-block';
          moonIcon.style.display = 'none';
        } else {
          sunIcon.style.display = 'none';
          moonIcon.style.display = 'inline-block';
        }
      }
    });
  }

  /**
   * Toggle between dark and light themes
   */
  function toggleTheme() {
    const currentTheme = document.documentElement.getAttribute('data-bs-theme') || DARK_THEME;
    const newTheme = currentTheme === DARK_THEME ? LIGHT_THEME : DARK_THEME;
    setTheme(newTheme);
  }

  /**
   * Initialize theme system
   */
  function initTheme() {
    // Set initial theme before DOM loads to prevent flash
    const theme = getPreferredTheme();
    setTheme(theme);
  }

  /**
   * Setup event listeners
   */
  function setupEventListeners() {
    // Theme toggle button click
    document.addEventListener('click', function(e) {
      const toggleBtn = e.target.closest('.theme-toggle');
      if (toggleBtn) {
        e.preventDefault();
        toggleTheme();
      }
    });

    // Listen for system theme changes
    window.matchMedia('(prefers-color-scheme: light)').addEventListener('change', function(e) {
      const storedTheme = getStoredTheme();
      if (!storedTheme) {
        setTheme(e.matches ? LIGHT_THEME : DARK_THEME);
      }
    });
  }

  /**
   * Navbar scroll effect
   */
  function setupNavbarScroll() {
    const navbar = document.querySelector('.navbar');
    if (!navbar) return;

    const handleScroll = function() {
      navbar.classList.toggle('nav-scrolled', window.scrollY > 24);
    };

    handleScroll();
    window.addEventListener('scroll', handleScroll, { passive: true });
  }

  /**
   * Reveal animation on scroll
   */
  function setupRevealAnimations() {
    const revealTargets = [
      '.card',
      '.list-group-item',
      '.table',
      '.alert:not(.alert-dismissible)',
      '.stat-item',
      '.feature-card'
    ];

    // Add reveal class to targets
    revealTargets.forEach(selector => {
      document.querySelectorAll(selector).forEach(el => {
        if (!el.classList.contains('reveal')) {
          el.classList.add('reveal');
        }
      });
    });

    // IntersectionObserver for reveal animations
    const observer = new IntersectionObserver(
      function(entries) {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            entry.target.classList.add('is-visible');
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.1, rootMargin: '0px 0px -50px 0px' }
    );

    document.querySelectorAll('.reveal').forEach(el => observer.observe(el));
  }

  /**
   * Smooth scroll for anchor links
   */
  function setupSmoothScroll() {
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
      anchor.addEventListener('click', function(e) {
        const targetId = this.getAttribute('href');
        if (targetId === '#') return;

        const target = document.querySelector(targetId);
        if (target) {
          e.preventDefault();
          target.scrollIntoView({
            behavior: 'smooth',
            block: 'start'
          });
        }
      });
    });
  }

  /**
   * Auto-dismiss alerts
   */
  function setupAlertAutoDismiss() {
    const alerts = document.querySelectorAll('.alert-dismissible');
    alerts.forEach(alert => {
      setTimeout(() => {
        const closeBtn = alert.querySelector('.btn-close');
        if (closeBtn && alert.parentNode) {
          closeBtn.click();
        }
      }, 5000);
    });
  }

  /**
   * Form validation styling
   */
  function setupFormValidation() {
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
      form.addEventListener('submit', function(e) {
        const invalidInputs = form.querySelectorAll(':invalid');
        invalidInputs.forEach(input => {
          input.classList.add('is-invalid');
        });
      });

      // Remove invalid class on input
      form.querySelectorAll('input, select, textarea').forEach(input => {
        input.addEventListener('input', function() {
          this.classList.remove('is-invalid');
        });
      });
    });
  }

  /**
   * Tooltip initialization
   */
  function initTooltips() {
    const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    if (window.bootstrap && window.bootstrap.Tooltip) {
      tooltipTriggerList.forEach(el => new window.bootstrap.Tooltip(el));
    }
  }

  /**
   * Popover initialization
   */
  function initPopovers() {
    const popoverTriggerList = document.querySelectorAll('[data-bs-toggle="popover"]');
    if (window.bootstrap && window.bootstrap.Popover) {
      popoverTriggerList.forEach(el => new window.bootstrap.Popover(el));
    }
  }

  /**
   * Counter animation for statistics
   */
  function setupCounterAnimation() {
    const counters = document.querySelectorAll('[data-counter]');

    const animateCounter = (el) => {
      const target = parseInt(el.getAttribute('data-counter'), 10);
      const duration = 2000;
      const step = target / (duration / 16);
      let current = 0;

      const updateCounter = () => {
        current += step;
        if (current < target) {
          el.textContent = Math.floor(current);
          requestAnimationFrame(updateCounter);
        } else {
          el.textContent = target;
        }
      };

      updateCounter();
    };

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            animateCounter(entry.target);
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.5 }
    );

    counters.forEach(counter => observer.observe(counter));
  }

  // Initialize theme immediately (before DOM load)
  initTheme();

  // Initialize everything else when DOM is ready
  document.addEventListener('DOMContentLoaded', function() {
    setupEventListeners();
    setupNavbarScroll();
    setupRevealAnimations();
    setupSmoothScroll();
    setupAlertAutoDismiss();
    setupFormValidation();
    initTooltips();
    initPopovers();
    setupCounterAnimation();

    // Update toggle icon after DOM loads
    const currentTheme = document.documentElement.getAttribute('data-bs-theme') || DARK_THEME;
    updateToggleIcon(currentTheme);
  });

  // Expose toggle function globally
  window.toggleTheme = toggleTheme;
  window.setTheme = setTheme;

})();
