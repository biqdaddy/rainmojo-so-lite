<?xml version="1.0" encoding="UTF-8"?>
<!--
  One stylesheet for both sitemap roots. It branches on the root node name so
  <sitemapindex> and <urlset> each get the table that suits them.

  Deliberately script-free and asset-free: it renders correctly under a strict
  Content-Security-Policy and when opened directly from a crawler-facing URL,
  which is often a different origin context than the app's own pages.

  Serve with Content-Type: text/xsl (or application/xslt+xml). Static hosts
  frequently guess the wrong MIME type for .xsl and silently break the
  transform, so a route handler is safer than a static asset.
-->
<xsl:stylesheet version="1.0"
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  xmlns:sm="http://www.sitemaps.org/schemas/sitemap/0.9">
<xsl:output method="html" encoding="UTF-8" indent="yes"/>

<xsl:template match="/">
  <html lang="en">
    <head>
      <meta charset="UTF-8"/>
      <meta name="viewport" content="width=device-width, initial-scale=1"/>
      <meta name="robots" content="noindex"/>
      <title>
        <xsl:choose>
          <xsl:when test="sm:sitemapindex">Sitemap index</xsl:when>
          <xsl:otherwise>Sitemap</xsl:otherwise>
        </xsl:choose>
      </title>
      <style>
        :root { color-scheme: light dark; }
        body {
          font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI",
                       sans-serif;
          margin: 0;
          padding: 2rem 1.5rem 4rem;
          line-height: 1.5;
          color: #17181c;
          background: #ffffff;
        }
        h1 { font-size: 1.4rem; margin: 0 0 0.25rem; letter-spacing: -0.01em; }
        .count { margin: 0 0 1.5rem; color: #5f6470; font-size: 0.9rem; }
        .back { display: inline-block; margin-bottom: 1.25rem;
                font-size: 0.9rem; color: #2757d6; }
        table { width: 100%; border-collapse: collapse; font-size: 0.9rem; }
        th {
          text-align: left;
          font-weight: 600;
          padding: 0.5rem 0.75rem;
          border-bottom: 2px solid #d7dae1;
          white-space: nowrap;
        }
        td {
          padding: 0.5rem 0.75rem;
          border-bottom: 1px solid #eceef2;
          vertical-align: top;
          word-break: break-all;
        }
        tr:nth-child(even) td { background: #fafbfc; }
        td.num { text-align: right; font-variant-numeric: tabular-nums;
                 white-space: nowrap; word-break: normal; }
        td.when { color: #5f6470; white-space: nowrap; word-break: normal; }
        a { color: #2757d6; text-decoration: none; }
        a:hover { text-decoration: underline; }
        @media (prefers-color-scheme: dark) {
          body { color: #e6e8ec; background: #14161a; }
          .count, td.when { color: #9aa0ac; }
          th { border-bottom-color: #333842; }
          td { border-bottom-color: #23262d; }
          tr:nth-child(even) td { background: #191c21; }
          a { color: #7ba1ff; }
        }
      </style>
    </head>
    <body>
      <xsl:choose>

        <xsl:when test="sm:sitemapindex">
          <h1>Sitemap index</h1>
          <p class="count">
            <xsl:value-of select="count(sm:sitemapindex/sm:sitemap)"/>
            <xsl:text> sitemaps</xsl:text>
          </p>
          <table>
            <thead>
              <tr>
                <th>Sitemap</th>
                <th>Last modified</th>
              </tr>
            </thead>
            <tbody>
              <xsl:for-each select="sm:sitemapindex/sm:sitemap">
                <tr>
                  <td>
                    <a href="{sm:loc}"><xsl:value-of select="sm:loc"/></a>
                  </td>
                  <td class="when"><xsl:value-of select="sm:lastmod"/></td>
                </tr>
              </xsl:for-each>
            </tbody>
          </table>
        </xsl:when>

        <xsl:otherwise>
          <h1>Sitemap</h1>
          <a class="back" href="/sitemap.xml">&#8592; Back to sitemap index</a>
          <p class="count">
            <xsl:value-of select="count(sm:urlset/sm:url)"/>
            <xsl:text> URLs</xsl:text>
          </p>
          <table>
            <thead>
              <tr>
                <th>URL</th>
                <th>Alternates</th>
                <th>Last modified</th>
              </tr>
            </thead>
            <tbody>
              <xsl:for-each select="sm:urlset/sm:url">
                <tr>
                  <td>
                    <a href="{sm:loc}"><xsl:value-of select="sm:loc"/></a>
                  </td>
                  <td class="num">
                    <xsl:value-of select="count(*[local-name()='link'])"/>
                  </td>
                  <td class="when"><xsl:value-of select="sm:lastmod"/></td>
                </tr>
              </xsl:for-each>
            </tbody>
          </table>
        </xsl:otherwise>

      </xsl:choose>
    </body>
  </html>
</xsl:template>
</xsl:stylesheet>
