# Website publishing

The [static showcase](../website/README.md) can be served from a domain root or
the repository's GitHub Pages subdirectory. Its images, clips, captions and links
use relative paths. No game executable, disc dump, BIOS, music pack or saves are
needed on the web server.

## Checks

The **Website checks and publishing** workflow validates changed website files
on pushes and pull requests. Local equivalents, from the repository root:

```sh
python tools/check_website.py
python -m unittest discover -s tests -p test_website.py -v
node --check website/dist/app.js
```

These checks catch missing files/anchors, broken GIF targets, duplicate IDs,
missing image descriptions, automatic video playback and paths that would break
under a repository URL. They do not replace listening to clips, reviewing the
layout or checking claims against gameplay evidence.

## GitHub Pages

Publishing is **manual**, from `main`, and runs only after the website checks
pass. Ordinary source pushes run checks without publishing the website.

1. In the repository's **Settings → Pages**, select **GitHub Actions** as the
   build source. This is a one-time repository-owner setup.
2. Open **Actions → Website checks and publishing → Run workflow**.
3. Select `main`, enable **Publish the website publicly**, and run it.
4. The `github-pages` deployment environment displays the resulting site URL.

The workflow uploads only `website/dist`. It uses GitHub's short-lived workflow
token; it does not require a personal token or an additional account secret.
Repository/environment protections still apply. See GitHub's
[custom workflow guide](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages).

## A custom domain

Once the public site is working, set the owned domain in **Settings → Pages**
before adding its DNS records at the domain provider. Use GitHub's current
[custom-domain instructions](https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site/managing-a-custom-domain-for-your-github-pages-site)
for the exact record type and values. With this Actions publishing route,
configure the domain in repository settings rather than relying on a CNAME file
inside the artifact. Enable HTTPS after the certificate is ready.

The separate private Sites preview reuses the project recorded in
`website/.openai/hosting.json`. Its host-managed certificate and GitHub Pages'
certificate are independent. A failure in that preview's certificate issuance
does not require rebuilding or changing the static website.
