import { defineConfig } from "vitepress";

export default defineConfig({
  title: "Project Lerna",
  description:
    "Autonomous SRE for Kubernetes: detect, diagnose, remediate in sandbox, validate—with human approval.",
  cleanUrls: true,
  themeConfig: {
    nav: [
      { text: "Home", link: "/" },
      { text: "Guide", link: "/guide/introduction" },
      { text: "Reference", link: "/reference/backend" },
    ],
    sidebar: {
      "/guide/": [
        {
          text: "Guide",
          items: [
            { text: "Introduction", link: "/guide/introduction" },
            { text: "Features", link: "/guide/features" },
            { text: "Tech stack", link: "/guide/tech-stack" },
            { text: "Getting started", link: "/guide/getting-started" },
            { text: "Architecture", link: "/guide/architecture" },
          ],
        },
      ],
      "/reference/": [
        {
          text: "Reference",
          items: [
            { text: "Backend API", link: "/reference/backend" },
            { text: "Observation layer", link: "/reference/observation-layer" },
          ],
        },
      ],
    },
    socialLinks: [
      {
        icon: "github",
        link: "https://github.com/KrithiAS10/hacktofuture4-A10",
      },
    ],
    footer: {
      message: "Project Lerna documentation",
      copyright: "Built from the repository README and layer docs.",
    },
    search: {
      provider: "local",
    },
  },
});
