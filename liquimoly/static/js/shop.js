/* Liqui Moly storefront - shared behaviour for every page.
 *
 * Previously this code was copy-pasted into 5 templates and rendered twice
 * per page (the first copy crashed because jQuery was not loaded yet).
 * Page data comes from <script id="shop-config" type="application/json">.
 */
(function ($) {
    "use strict";

    var configEl = document.getElementById("shop-config");
    var CFG = configEl ? JSON.parse(configEl.textContent) : {};
    var T = CFG.i18n || {};
    var URLS = CFG.urls || {};
    var csrfToken = CFG.csrfToken || "";

    var mobileQuery = window.matchMedia("(max-width: 991.98px)");

    /* ------------------------------------------------------------------
     * Navbar
     * ------------------------------------------------------------------ */
    function initNavbar() {
        var $menu = $("#mainNavbar");
        var $icon = $("#burgerIcon");
        var $search = $("#mobileSearch");

        function closeMenu() {
            $menu.removeClass("show");
            $icon.removeClass("bi-x-lg").addClass("bi-list");
            $("#customBurgerBtn").attr("aria-expanded", "false");
        }

        $("#mobileSearchBtn").on("click", function () {
            $search.toggleClass("is-open");
            if ($search.hasClass("is-open")) {
                closeMenu();
                $("#mobileSearchInput").trigger("focus");
            }
        });

        $("#customBurgerBtn").on("click", function (e) {
            e.preventDefault();
            $search.removeClass("is-open");
            var open = !$menu.hasClass("show");
            $menu.toggleClass("show", open);
            $icon.toggleClass("bi-list", !open).toggleClass("bi-x-lg", open);
            $(this).attr("aria-expanded", open ? "true" : "false");
        });

        // Only react when crossing the breakpoint (mobile browsers fire
        // "resize" while scrolling, which used to close the menu).
        var onChange = function (e) { if (!e.matches) { closeMenu(); $search.removeClass("is-open"); } };
        if (mobileQuery.addEventListener) { mobileQuery.addEventListener("change", onChange); }
        else if (mobileQuery.addListener) { mobileQuery.addListener(onChange); }
    }

    /* ------------------------------------------------------------------
     * Region picker
     * ------------------------------------------------------------------ */
    function initPlacePicker() {
        var modalEl = document.getElementById("placeModal");
        if (modalEl && !CFG.hasPlace && window.bootstrap) {
            new bootstrap.Modal(modalEl).show();
        }

        $(document).on("click", ".place-btn", function () {
            var $btn = $(this).prop("disabled", true);
            fetch(URLS.setPlace, {
                method: "POST",
                headers: { "X-CSRFToken": csrfToken },
                credentials: "same-origin",
                body: new URLSearchParams({ place_id: $btn.data("id") })
            }).then(function () { location.reload(); })
              .catch(function () { $btn.prop("disabled", false); });
        });
    }

    /* ------------------------------------------------------------------
     * Floating buttons, alerts, PWA install
     * ------------------------------------------------------------------ */
    function initChrome() {
        var toTop = document.getElementById("scrollToTop");
        var install = document.getElementById("add-to-home-screen");
        var ticking = false;

        window.addEventListener("scroll", function () {
            if (ticking) { return; }
            ticking = true;
            window.requestAnimationFrame(function () {
                var far = window.scrollY > 1000;
                if (toTop) { toTop.classList.toggle("is-visible", far); }
                if (install) { install.parentElement.classList.toggle("pe-5", far); }
                ticking = false;
            });
        }, { passive: true });

        if (toTop) {
            toTop.addEventListener("click", function (e) {
                e.preventDefault();
                window.scrollTo({ top: 0, behavior: "smooth" });
            });
        }

        // auto-dismiss flash messages
        setTimeout(function () {
            $(".auto-dismiss-alert").each(function () {
                if (window.bootstrap) { bootstrap.Alert.getOrCreateInstance(this).close(); }
                else { $(this).remove(); }
            });
        }, 5000);

        var deferredPrompt = null;
        if (install) {
            window.addEventListener("beforeinstallprompt", function (e) {
                e.preventDefault();
                deferredPrompt = e;
                install.style.display = "block";
            });
            install.addEventListener("click", function () {
                install.style.display = "none";
                if (deferredPrompt) {
                    deferredPrompt.prompt();
                    deferredPrompt = null;
                }
            });
            window.addEventListener("appinstalled", function () {
                install.style.display = "none";
                deferredPrompt = null;
            });
        }

        if ("serviceWorker" in navigator && URLS.serviceWorker) {
            window.addEventListener("load", function () {
                navigator.serviceWorker.register(URLS.serviceWorker).catch(function () {});
            });
        }
    }

    /* ------------------------------------------------------------------
     * Google map (sidebar): load the iframe only when it scrolls into view
     * ------------------------------------------------------------------ */
    function initMap() {
        var wrapper = document.getElementById("googleMapWrapper");
        if (!wrapper || !wrapper.dataset.src) { return; }

        var load = function () {
            var iframe = document.createElement("iframe");
            iframe.src = wrapper.dataset.src;
            iframe.title = (T.map || "Map") + ": " + (wrapper.dataset.place || "");
            iframe.loading = "lazy";
            iframe.allowFullscreen = true;
            iframe.referrerPolicy = "strict-origin-when-cross-origin";
            wrapper.replaceChildren(iframe);
        };

        if ("IntersectionObserver" in window) {
            var io = new IntersectionObserver(function (entries) {
                if (entries[0].isIntersecting) { load(); io.disconnect(); }
            }, { rootMargin: "250px 0px" });
            io.observe(wrapper);
        } else {
            load();
        }
    }

    /* ------------------------------------------------------------------
     * Hero slider
     * ------------------------------------------------------------------ */
    function initHero() {
        var el = document.querySelector(".hero.splide");
        if (!el || typeof Splide === "undefined") { return; }
        var slides = el.querySelectorAll(".splide__slide").length;
        var splide = new Splide(el, {
            type: slides > 1 ? "loop" : "slide",
            perPage: 1,
            autoplay: slides > 1,
            interval: 5000,
            speed: 900,
            pauseOnHover: true,
            arrows: false,
            pagination: slides > 1,
            lazyLoad: "nearby",
            drag: slides > 1
        });
        splide.on("mounted", function () { el.classList.add("is-initialized"); });
        splide.mount();
    }

    /* ------------------------------------------------------------------
     * Add to cart + car parameters modal
     * ------------------------------------------------------------------ */
    function validateCarNumber(value, type) {
        var cleanVal = value.toUpperCase().trim().replace(/[\s\-]/g, "");

        if (!cleanVal) {
            return { isValid: false, message: "Nomeri giriziň!" };
        }

        if (type === "edara") {
            if (!/^\d{4}[A-Z]{3}$/.test(cleanVal)) {
                return {
                    isValid: false,
                    message: "Edara nomeri nadogry: 4 sifr we soňy 3 harp bolmaly! (Mysal: 1234AGH)"
                };
            }
            return { isValid: true, message: "" };
        }

        if (type === "hususy") {
            var match = cleanVal.match(/^([A-Z]{2})(\d{3,4})([A-Z]{2})$/);
            if (!match) {
                return {
                    isValid: false,
                    message: "Hususy nomer nadogry! Formaty: XX 0000 XX (Mysal: DB 1234 AG)"
                };
            }

            var front = match[1];
            var end = match[3];

            if (front[0] === front[1]) {
                return { isValid: false, message: "Öňündäki 2 harp bir meňzeş bolup bilmeyär (AA, BB...)!" };
            }

            var forbiddenChars = ["Ç", "Ň", "Ş", "Ö", "Ý", "Ź", "X"];
            for (var i = 0; i < cleanVal.length; i++) {
                if (forbiddenChars.indexOf(cleanVal[i]) !== -1) {
                    return { isValid: false, message: "'" + cleanVal[i] + "' harpy nomerde bolup bilmeyär!" };
                }
            }

            if (front === "AM") {
                return { isValid: false, message: "Öňündäki harplar 'AM' bolup bilmeyär!" };
            }

            if (["AH", "AG", "DZ", "BN", "MR", "LB"].indexOf(front) !== -1) {
                return { isValid: false, message: "Öňündäki harplar welaýat kody (" + front + ") bolup bilmeyär!" };
            }

            var validEndings = ["AG", "AH", "BN", "DZ", "LB", "MR", "AK"];
            if (validEndings.indexOf(end) === -1) {
                return {
                    isValid: false,
                    message: "Soňky harplar diňe welaýat kody bolmaly (" + validEndings.join(", ") + ")!"
                };
            }
            return { isValid: true, message: "" };
        }

        return { isValid: true, message: "" };
    }

    function markRequired($el) {
        var ok = !!$el.val();
        $el.toggleClass("is-invalid", !ok);
        return ok;
    }

    function validateModalForm() {
        var isValid = true;
        isValid = markRequired($("#brand")) && isValid;
        isValid = markRequired($("#model")) && isValid;
        isValid = markRequired($("#year")) && isValid;

        var type = $("#numberType").find("option:selected").data("type");
        if (!$("#numberType").val() || !type) {
            $("#numberType").addClass("is-invalid");
            isValid = false;
        } else {
            $("#numberType").removeClass("is-invalid");
        }

        var result = validateCarNumber($("#car_number").val() || "", type);
        if (!result.isValid) {
            $("#car_number").addClass("is-invalid").removeClass("is-valid");
            $("#car_number_error").text(result.message).removeClass("d-none");
            isValid = false;
        } else {
            $("#car_number").addClass("is-valid").removeClass("is-invalid");
            $("#car_number_error").addClass("d-none").text("");
        }
        return isValid;
    }

    function resetModelSelect() {
        var $model = $("#model").empty();
        $("<option>", { value: "", selected: true, disabled: true, text: T.chooseModel || "--" }).appendTo($model);
        return $model;
    }

    function loadModels(brandId) {
        $.ajax({
            url: URLS.getByBrand,
            type: "POST",
            dataType: "json",
            data: { brand_id: brandId, csrfmiddlewaretoken: csrfToken },
            success: function (response) {
                var $model = resetModelSelect();
                $.each(response, function (_, item) {
                    // .text() - brand titles are never interpreted as HTML
                    $("<option>", { value: item.id, text: item.title }).appendTo($model);
                });
                $("#model-section").removeClass("d-none");
            },
            error: function (xhr, status, error) {
                console.error("Model Loading Error:", error);
            }
        });
    }

    function markAdded($btn) {
        $btn.val("added")
            .html("<i class='bi bi-check-lg'></i> " + (T.added || "OK"))
            .removeAttr("data-bs-toggle")
            .removeAttr("data-bs-target");
    }

    function updateCartCount(total) {
        if (total !== undefined && total > 0) {
            $(".cart-count").text(total);
        }
    }

    function initCart() {
        var cartIds = (CFG.cartProductIds || []).map(String);

        // Buttons for products already in the cart -> "Added" (link to cart)
        $(".add-to-cart").each(function () {
            var $btn = $(this);
            if (cartIds.indexOf(String($btn.val())) !== -1) {
                markAdded($btn);
            } else if ($btn.data("requiresParameters")) {
                $btn.attr("data-bs-toggle", "modal").attr("data-bs-target", "#ServiceModal");
            } else {
                $btn.removeAttr("data-bs-toggle").removeAttr("data-bs-target");
            }
        });

        function addDirect(productId, $btn) {
            $btn.prop("disabled", true);
            $.ajax({
                url: URLS.addToCart,
                method: "POST",
                dataType: "json",
                data: { product_id: productId, csrfmiddlewaretoken: csrfToken },
                success: function (response) {
                    $btn.prop("disabled", false);
                    markAdded($btn);
                    updateCartCount(response.total);
                },
                error: function (xhr, status, error) {
                    console.error("AJAX Error:", error);
                    alert(T.addError || "Error");
                    $btn.prop("disabled", false);
                }
            });
        }

        $(document).on("click", ".add-to-cart", function () {
            var $btn = $(this);
            var productId = $btn.val();

            if (productId === "added") {
                window.location.href = URLS.cart;
                return;
            }
            if ($btn.data("requiresParameters")) {
                $(".modal-cart").val(productId);
            } else {
                addDirect(productId, $btn);
            }
        });

        if (!document.getElementById("ServiceModal")) { return; }

        // progressive car-parameters form
        $("#brand").on("change", function () {
            if ($(this).val()) {
                $("#model-section").removeClass("d-none");
                loadModels($(this).val());
            }
        });
        $("#model").on("change", function () { if ($(this).val()) { $("#year-section").removeClass("d-none"); } });
        $("#year").on("change", function () { if ($(this).val()) { $("#engine-section").removeClass("d-none"); } });
        $("#engine").on("change", function () { if ($(this).val()) { $("#casting-type-section").removeClass("d-none"); } });
        $("#casting-type").on("change", function () { if ($(this).val()) { $("#number-section").removeClass("d-none"); } });

        $("#numberType").on("change", function () {
            var type = $(this).find("option:selected").data("type");
            var $input = $("#car_number");
            if ($(this).val()) {
                $("#car-number-section").removeClass("d-none");
                if (type === "edara") { $input.attr("placeholder", "1234 AGH"); }
                else if (type === "hususy") { $input.attr("placeholder", "DB 1234 AG"); }
                if ($input.val().trim() !== "") { $input.trigger("input"); }
            }
        });

        $("#car_number").on("input blur", function () {
            var value = $(this).val();
            var type = $("#numberType").find("option:selected").data("type");
            var $error = $("#car_number_error");
            if (!type) { return; }

            var result = validateCarNumber(value, type);
            if (!result.isValid && value.trim() !== "") {
                $(this).addClass("is-invalid").removeClass("is-valid");
                $error.text(result.message).removeClass("d-none");
            } else if (result.isValid) {
                $(this).addClass("is-valid").removeClass("is-invalid");
                $error.addClass("d-none").text("");
            } else {
                $(this).removeClass("is-valid is-invalid");
                $error.addClass("d-none").text("");
            }
        });

        $(".modal-cart").on("click", function () {
            var $self = $(this);
            var productId = $self.val();

            if (!validateModalForm()) { return false; }

            var selected = function (sel) { return $(sel + " option:selected").text().trim(); };
            var $addBtn = $('.add-to-cart[value="' + productId + '"]');

            $self.prop("disabled", true);
            $.ajax({
                url: URLS.addToCart,
                method: "POST",
                dataType: "json",
                data: {
                    product_id: productId,
                    brand: selected("#brand"),
                    model: selected("#model"),
                    year: selected("#year"),
                    engine: selected("#engine"),
                    casting_type: selected("#casting-type"),
                    car_number_type: selected("#numberType"),
                    car_number: ($("#car_number").val() || "").toUpperCase().trim(),
                    csrfmiddlewaretoken: csrfToken
                },
                success: function (response) {
                    $self.prop("disabled", false);
                    markAdded($addBtn);
                    updateCartCount(response.total);
                    var modalEl = document.getElementById("ServiceModal");
                    if (modalEl && window.bootstrap) {
                        bootstrap.Modal.getOrCreateInstance(modalEl).hide();
                    }
                },
                error: function (xhr, status, error) {
                    console.error("AJAX Error:", error);
                    alert(T.addError || "Error");
                    $self.prop("disabled", false);
                }
            });
        });

        $("#ServiceModal").on("hidden.bs.modal", function () {
            $("#brand, #year, #numberType, #engine, #casting-type").val("");
            $("#car_number").val("").attr("placeholder", "XX 0000 XX");
            resetModelSelect();
            $("#model-section, #year-section, #number-section, #car-number-section, #engine-section, #casting-type-section").addClass("d-none");
            $("#brand, #model, #year, #numberType, #car_number, #engine, #casting-type").removeClass("is-invalid is-valid");
            $("#car_number_error").addClass("d-none").text("");
        });
    }

    $(function () {
        initNavbar();
        initPlacePicker();
        initChrome();
        initMap();
        initHero();
        initCart();
    });

    window.LiquiMoly = { validateCarNumber: validateCarNumber, config: CFG };
})(jQuery);
