import { html } from "../../vendor/htm-preact-standalone.module.js";

const NAV_ITEMS = [
  { route: "/", label: "Home" },
  { route: "/consult", label: "Consultation" },
  { route: "/result", label: "Result" },
  { route: "/rules", label: "Rules" },
  { route: "/queries", label: "Queries" },
  { route: "/about", label: "About" },
];

export function Header({ route }) {
  return html`
    <header class="site-header">
      <div class="header-inner">
        <a class="brand" href="#/">
          <img class="brand-icon" src="favicon.svg" alt="" width="28" height="28" />
          <span>GastroKG</span>
        </a>
        <nav class="nav-links" aria-label="Main navigation">
          ${NAV_ITEMS.map((item) => html`
            <a
              key=${item.route}
              class="nav-link"
              href=${`#${item.route}`}
              aria-current=${route === item.route ? "page" : undefined}
            >
              ${item.label}
            </a>
          `)}
        </nav>
      </div>
    </header>
  `;
}
