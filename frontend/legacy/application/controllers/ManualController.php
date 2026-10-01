<?php

/**
 * RASTATIME 2026-10-01 - the user manual, readable in the browser.
 *
 * Serves the Markdown manuals of the repository rendered as HTML inside
 * the application layout (Help -> User Manual):
 *
 *   /manual                       index in the user's UI language
 *   /manual/<lang>                index (en | de | fr | es)
 *   /manual/<lang>/<CHAPTER>      docs/manual[/<lang>]/<CHAPTER>.md
 *   /manual/doc/<repo path>       any other Markdown file below docs/
 *                                 (operator runbooks) and the two root
 *                                 documents the manuals link to
 *
 * Relative links between the files are rewritten to these routes, so
 * the manual can be browsed like a small site; anything the whitelist
 * does not cover points at the GitHub project instead.  Rendering is
 * Parsedown (library/Parsedown.php, MIT) - the manuals are our own
 * files, so safe mode stays off and their few inline HTML tags pass.
 */
class ManualController extends Zend_Controller_Action
{
    /** Language -> manual directory relative to the repository root. */
    private const LANG_DIRS = [
        'en' => 'docs/manual',
        'de' => 'docs/manual/de',
        'fr' => 'docs/manual/fr',
        'es' => 'docs/manual/es',
    ];

    private const LANG_LABELS = [
        'en' => 'English',
        'de' => 'Deutsch',
        'fr' => 'Français',
        'es' => 'Español',
    ];

    private const INDEX_CHAPTER = 'USER_MANUAL';

    /** Root-level Markdown files the manuals link to (repo-relative). */
    private const ROOT_DOCS = [
        'USER_MANUAL.md',
        'RASTATIME_ARCHITECTURE_DRAFT_v0.1.md',
    ];

    public function indexAction()
    {
        $this->serve();
    }

    /**
     * /manual/<lang>/<CHAPTER> arrives on the default module route as
     * action "<lang>" - every such action lands here.  (A route of its own
     * would break the navigation menu: the menu assembles all links with
     * the route that matched the request.)
     */
    public function __call($method, $args)
    {
        if (substr($method, -6) === 'Action') {
            $this->serve();

            return;
        }

        return parent::__call($method, $args);
    }

    private function serve()
    {
        Zend_Layout::getMvcInstance()->assign('parent_page', 'Help');
        $this->_helper->viewRenderer('index');

        // the path after the base url: manual[/<lang>[/<chapter or doc path>]]
        $parts = explode('/', trim(str_replace('\\', '/', (string) $this->getRequest()->getPathInfo()), '/'), 3);
        $lang = strtolower($parts[1] ?? '');
        $chapter = $parts[2] ?? '';

        if ($lang === 'doc') {
            // /manual/doc/docs/operator/INSTALL - a repository document;
            // an unknown one falls back to the manual index
            $relPath = $this->sanitizeDocPath($chapter);
            if ($relPath === null) {
                $this->_helper->redirector->gotoUrlAndExit($this->view->baseUrl('manual/' . self::uiLanguage()));
            }
            $this->renderDocument($relPath, null, null);

            return;
        }

        if (!isset(self::LANG_DIRS[$lang])) {
            // /manual (or an unknown language) -> the index in the UI
            // language, with a clean URL
            $this->_helper->redirector->gotoUrlAndExit($this->view->baseUrl('manual/' . self::uiLanguage()));
        }
        if ($chapter === '' || $chapter === 'index') {
            $chapter = self::INDEX_CHAPTER;
        }
        $relPath = preg_match('/^[A-Za-z0-9_]+$/', $chapter) ? self::chapterPath($lang, $chapter) : null;
        if ($relPath === null) {
            // unknown chapter: the index of that language
            $this->_helper->redirector->gotoUrlAndExit($this->view->baseUrl('manual/' . $lang));
        }
        $this->renderDocument($relPath, $lang, $chapter);
    }

    /**
     * Repository-relative path of a chapter, null when the file is missing.
     * The English index lives at the repository root.
     */
    private static function chapterPath($lang, $chapter)
    {
        if ($lang === 'en' && $chapter === self::INDEX_CHAPTER) {
            $rel = 'USER_MANUAL.md';
        } else {
            $rel = self::LANG_DIRS[$lang] . '/' . $chapter . '.md';
        }

        return is_file(self::repoRoot() . '/' . $rel) ? $rel : null;
    }

    /**
     * Whitelist for /manual/doc/<path>: Markdown below docs/ or one of the
     * root documents; no traversal, no other file types.
     */
    private function sanitizeDocPath($path)
    {
        $path = trim(str_replace('\\', '/', $path), '/');
        if ($path === '' || !preg_match('#^[A-Za-z0-9_./-]+$#', $path) || strpos($path, '..') !== false) {
            return null;
        }
        if (substr($path, -3) !== '.md') {
            $path .= '.md';
        }
        $allowed = strpos($path, 'docs/') === 0 || in_array($path, self::ROOT_DOCS, true);
        if (!$allowed || !is_file(self::repoRoot() . '/' . $path)) {
            return null;
        }

        return $path;
    }

    private function renderDocument($relPath, $lang, $chapter)
    {
        $markdown = file_get_contents(self::repoRoot() . '/' . $relPath);
        if ($markdown === false) {
            throw new Zend_Controller_Action_Exception('Document not readable', 500);
        }

        require_once APPLICATION_PATH . '/../library/Parsedown.php';
        $parser = new Parsedown();
        $parser->setBreaksEnabled(false);
        $html = $parser->text($markdown);
        $html = $this->rewriteLinks($html, dirname($relPath));
        $html = self::addHeadingIds($html);

        $title = 'User Manual';
        if (preg_match('/^#\s+(.+)$/m', $markdown, $m)) {
            $title = trim($m[1]);
        }

        // language bar: the same chapter in every language that has it
        $languages = [];
        if ($lang !== null) {
            foreach (self::LANG_DIRS as $code => $dir) {
                if (self::chapterPath($code, $chapter) !== null) {
                    $languages[$code] = [
                        'label' => self::LANG_LABELS[$code],
                        'url' => $this->view->baseUrl('manual/' . $code . ($chapter === self::INDEX_CHAPTER ? '' : '/' . $chapter)),
                        'current' => $code === $lang,
                    ];
                }
            }
        }

        $this->view->headTitle()->setSeparator(' – ');
        $this->view->headTitle($title);
        $this->view->manualHtml = $html;
        $this->view->manualTitle = $title;
        $this->view->manualLang = $lang ?: self::uiLanguage();
        $this->view->manualLanguages = $languages;
        $this->view->manualIndexUrl = $this->view->baseUrl('manual/' . ($lang ?: self::uiLanguage()));
        $this->view->manualIsIndex = $lang !== null && $chapter === self::INDEX_CHAPTER;
        $this->view->manualGithubUrl = RASTATIME_GITHUB_URL . '/blob/main/' . $relPath;
    }

    /**
     * Rewrites the relative Markdown links of a document to the manual
     * routes: ./CHAPTER.md, ../fr/USER_MANUAL.md, ../../operator/INSTALL.md,
     * ../../../USER_MANUAL.md - fragments are kept.  Absolute URLs and
     * in-page anchors pass through untouched; a repository file outside
     * the whitelist goes to GitHub.
     */
    private function rewriteLinks($html, $docDir)
    {
        return preg_replace_callback(
            '/(<a\s[^>]*href=")([^"]+)(")/i',
            function ($m) use ($docDir) {
                $href = html_entity_decode($m[2], ENT_QUOTES, 'UTF-8');
                if ($href === '' || $href[0] === '#' || preg_match('#^[a-z][a-z0-9+.-]*:#i', $href) || $href[0] === '/') {
                    return $m[0];
                }
                $fragment = '';
                if (($pos = strpos($href, '#')) !== false) {
                    $fragment = substr($href, $pos);
                    $href = substr($href, 0, $pos);
                }
                if (substr($href, -3) !== '.md') {
                    return $m[0];
                }
                $target = self::normalizePath(($docDir === '.' ? '' : $docDir . '/') . $href);
                $url = self::routeFor($target);
                if ($url === null) {
                    $url = RASTATIME_GITHUB_URL . '/blob/main/' . $target;
                } else {
                    $url = $this->view->baseUrl($url);
                }

                return $m[1] . htmlspecialchars($url . $fragment, ENT_QUOTES, 'UTF-8') . $m[3];
            },
            $html
        );
    }

    /** Manual route for a repository-relative Markdown path, null if none. */
    private static function routeFor($target)
    {
        if ($target === 'USER_MANUAL.md') {
            return 'manual/en';
        }
        foreach (['de', 'fr', 'es'] as $code) {
            $dir = self::LANG_DIRS[$code] . '/';
            if (strpos($target, $dir) === 0 && preg_match('/^[A-Za-z0-9_]+\.md$/', substr($target, strlen($dir)))) {
                $chapter = substr($target, strlen($dir), -3);

                return 'manual/' . $code . ($chapter === self::INDEX_CHAPTER ? '' : '/' . $chapter);
            }
        }
        if (preg_match('#^docs/manual/([A-Za-z0-9_]+)\.md$#', $target, $m)) {
            return 'manual/en/' . $m[1];
        }
        if (strpos($target, 'docs/') === 0 || in_array($target, self::ROOT_DOCS, true)) {
            return 'manual/doc/' . substr($target, 0, -3);
        }

        return null;
    }

    /** Collapses ./ and ../ segments of a repository-relative path. */
    private static function normalizePath($path)
    {
        $out = [];
        foreach (explode('/', str_replace('\\', '/', $path)) as $seg) {
            if ($seg === '' || $seg === '.') {
                continue;
            }
            if ($seg === '..') {
                array_pop($out);

                continue;
            }
            $out[] = $seg;
        }

        return implode('/', $out);
    }

    /**
     * GitHub-style heading ids so the manuals' #section links work:
     * lower case, punctuation dropped, spaces to dashes, duplicates
     * numbered.
     */
    private static function addHeadingIds($html)
    {
        $seen = [];

        return preg_replace_callback(
            '/<h([1-6])>(.*?)<\/h\1>/su',
            function ($m) use (&$seen) {
                $text = html_entity_decode(strip_tags($m[2]), ENT_QUOTES, 'UTF-8');
                $slug = mb_strtolower($text, 'UTF-8');
                $slug = preg_replace('/[^\p{L}\p{N}\s_-]/u', '', $slug);
                $slug = preg_replace('/\s+/u', '-', trim($slug));
                if ($slug === '') {
                    $slug = 'section';
                }
                if (isset($seen[$slug])) {
                    $slug .= '-' . (++$seen[$slug]);
                } else {
                    $seen[$slug] = 0;
                }

                return '<h' . $m[1] . ' id="' . htmlspecialchars($slug, ENT_QUOTES, 'UTF-8') . '">' . $m[2] . '</h' . $m[1] . '>';
            },
            $html
        );
    }

    /** Two-letter manual language from the user's UI locale, en as fallback. */
    private static function uiLanguage()
    {
        $code = strtolower(substr((string) Application_Model_Preference::GetLocale(), 0, 2));

        return isset(self::LANG_DIRS[$code]) ? $code : 'en';
    }

    private static function repoRoot()
    {
        return realpath(APPLICATION_PATH . '/../../..');
    }
}
