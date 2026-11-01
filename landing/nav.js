/* Riverfed: shared top nav (single source of truth).
 *
 * Every page (/, /about, /studio, /wiki) drops in:
 *     <div data-pa-nav></div>
 *     <script src="/nav.js" defer></script>
 * and gets the SAME nav. This keeps the bar consistent across pages.
 *
 * Self-contained on purpose: it injects its own scoped CSS (`.pa-nav*`,
 * hardcoded colours) so it renders identically regardless of each page's
 * own variables/classes, and can't collide with page styles like `.row`
 * or `.brand`. The active link is derived from the current path. Direct
 * file previews use the equivalent HTML files instead of server routes.
 */
(function () {
  "use strict";

  var path = (location.pathname || "/").replace(/\/+$/, "") || "/";
  var isFilePreview = location.protocol === "file:";
  var isLandingFile = isFilePreview && path.indexOf("/landing/") !== -1;

  var LINKS = [
    { href: "/",      label: "Add" },
    { href: "/wiki",  label: "Knowledge" }
  ];

  function routeHref(route) {
    if (!isFilePreview) return route;

    if (isLandingFile) {
      if (route === "/") return "../index.html";
      if (route === "/about") return "index.html";
      return route.slice(1) + ".html";
    }

    if (route === "/") return "index.html";
    if (route === "/about") return "landing/index.html";
    return "landing/" + route.slice(1) + ".html";
  }

  function activeRoute() {
    if (!isFilePreview) {
      if (path === "/" || path === "/index.html") return "/";
      if (path === "/wiki" || path.indexOf("/wiki/") === 0) return "/wiki";
      if (path === "/studio" || path.indexOf("/studio/") === 0) return "/studio";
      if (path === "/about" || path.indexOf("/about/") === 0 ||
          path === "/landing" || path.indexOf("/landing/") === 0) {
        return "/about";
      }
      return "";
    }

    var filename = path.split("/").pop() || "index.html";
    if (isLandingFile && filename === "wiki.html") return "/wiki";
    if (isLandingFile && filename === "studio.html") return "/studio";
    if (isLandingFile && filename === "index.html") return "/about";
    if (!isLandingFile && filename === "index.html") return "/";
    return "";
  }

  var currentRoute = activeRoute();

  /* "Porcelain" light theme (2026-07 redesign): sober neutrals, one accent,
     no gradients, no glow. Quiet text links, compact CTA. Hardcoded on purpose
     (see header comment). */
  var CSS = [
    '.pa-nav{position:sticky;top:0;z-index:50;',
    '--pa-font-sans:"Inter",-apple-system,BlinkMacSystemFont,"Segoe UI",system-ui,sans-serif;',
    '--pa-font-mono:"JetBrains Mono","SF Mono",Menlo,Consolas,monospace;',
    'background:rgba(247,248,250,0.88);',
    '-webkit-backdrop-filter:saturate(180%) blur(14px);backdrop-filter:saturate(180%) blur(14px);',
    'border-bottom:1px solid #eaedf2;',
    'font-family:var(--pa-font-sans);}',
    '.pa-nav *{box-sizing:border-box;}',
    '.pa-nav__inner{display:flex;align-items:center;justify-content:space-between;',
    'height:68px;max-width:1120px;margin:0 auto;padding:0 24px;}',
    '.pa-nav__brand{display:inline-flex;align-items:baseline;',
    'font-weight:900;font-size:17px;letter-spacing:-0.045em;color:#15171c;text-decoration:none;}',
    '.pa-nav__dot{color:#1d9e66;}',
    '.pa-nav__links{display:flex;gap:26px;align-items:center;}',
    '.pa-nav__link{color:#5c6470;font-size:14px;font-weight:500;padding:6px 0;',
    'text-decoration:none;transition:color .15s;}',
    '.pa-nav__link:hover{color:#15171c;}',
    '.pa-nav__link--active{color:#15171c;font-weight:600;',
    'box-shadow:inset 0 -2px 0 #157347;}',
    '.pa-nav__brand:focus-visible,.pa-nav__link:focus-visible,.pa-nav__cta:focus-visible{',
    'outline:3px solid rgba(21,115,71,.35);outline-offset:4px;border-radius:3px;}',
    '.pa-nav__cta,.pa-nav__cta:link,.pa-nav__cta:visited{',
    'background:#15171c;color:#fff;',
    'padding:9px 16px;border-radius:7px;font-size:14px;font-weight:600;text-decoration:none;',
    'transition:background .15s ease;}',
    '.pa-nav__cta:hover,.pa-nav__cta:active{color:#fff;background:#157347;}',
    '@media(max-width:720px){',
    '.pa-nav__inner{height:60px;padding:0 10px;}',
    '.pa-nav__brand{font-size:14px;}',
    '.pa-nav__links{gap:10px;}',
    '.pa-nav__link{font-size:12px;padding:6px 0;}',
    '.pa-nav__cta,.pa-nav__cta:link,.pa-nav__cta:visited{font-size:12px;padding:7px 9px;}',
    '}'
  ].join("");

  var linksHtml = LINKS.map(function (l) {
    var isCurrent = currentRoute === l.href;
    var cls = "pa-nav__link" + (isCurrent ? " pa-nav__link--active" : "");
    var current = isCurrent ? ' aria-current="page"' : "";
    return '<a class="' + cls + '" href="' + routeHref(l.href) + '"' +
      current + ">" + l.label + "</a>";
  }).join("");

  var brandCurrent = currentRoute === "/about" ? ' aria-current="page"' : "";
  var studioCurrent = currentRoute === "/studio" ? ' aria-current="page"' : "";
  var html =
    '<nav class="pa-nav" aria-label="Primary">' +
      '<div class="pa-nav__inner">' +
        '<a class="pa-nav__brand" href="' + routeHref("/about") + '"' +
          ' aria-label="Riverfed: About"' + brandCurrent + ">" +
          'Riverfed<span class="pa-nav__dot">.</span></a>' +
        '<div class="pa-nav__links">' +
          linksHtml +
          '<a class="pa-nav__cta" href="' + routeHref("/studio") + '"' +
            studioCurrent + ">Create</a>" +
        "</div>" +
      "</div>" +
    "</nav>";

  function mount() {
    var style = document.createElement("style");
    style.setAttribute("data-pa-nav-style", "");
    style.textContent = CSS;
    document.head.appendChild(style);

    var slot = document.querySelector("[data-pa-nav]");
    if (slot) {
      slot.outerHTML = html;            // replace the placeholder
    } else {
      document.body.insertAdjacentHTML("afterbegin", html);  // fallback
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", mount);
  } else {
    mount();
  }
})();
