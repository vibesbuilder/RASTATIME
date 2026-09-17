<?php

/**
 * Created by PhpStorm.
 * User: asantoni
 * Date: 11/09/15
 * Time: 2:47 PM.
 */
class AirtimeTableView
{
    private static function _getTableJavaScriptDependencies()
    {
        // RASTATIME 2026-09-17 (JS-modernization 5b): DataTables 1.13 is the
        // only core; the 2012 ColVis/ColReorder are gone, Buttons (+colVis)
        // and ColReorder 1.6 are the extensions.  The version-agnostic helper
        // plugins (pluginAPI / fnSetFilteringDelay / FixedColumns /
        // FixedHeader / columnFilter) load unchanged ($.browser via shim).
        $deps = [
            'js/airtime/widgets/table.js',
            'js/datatables-1.13/js/jquery.dataTables.min.js',
            'js/datatables/plugin/dataTables.pluginAPI.js',
            'js/datatables/plugin/dataTables.fnSetFilteringDelay.js',
        ];
        $deps[] = 'js/datatables-1.13/extensions/dataTables.buttons.min.js';
        $deps[] = 'js/datatables-1.13/extensions/buttons.colVis.min.js';
        $deps[] = 'js/datatables-1.13/extensions/dataTables.colReorder.min.js';
        $deps[] = 'js/datatables/plugin/dataTables.FixedColumns.js';
        $deps[] = 'js/datatables/plugin/dataTables.FixedHeader.js';
        $deps[] = 'js/datatables/plugin/dataTables.columnFilter.js';

        return $deps;
    }

    public static function injectTableJavaScriptDependencies(&$headScript)
    {
        foreach (self::_getTableJavaScriptDependencies() as $path) {
            $headScript->appendFile(Assets::url($path), 'text/javascript');
        }
    }

    /**
     * RASTATIME 2026-06-03 (JS-modernization stage 2): the DataTables CSS must
     * match the loaded extension generation.  On ?jq3 the modern Buttons (colvis)
     * + ColReorder 1.6 are loaded, which ship their own stylesheets; the 2012
     * ColVis.css / colReorder.css do not style the modern markup (e.g. the
     * library "Columns" button would otherwise render unstyled / invisible).  On
     * the legacy default (1.9) keep the original stylesheets.
     */
    public static function injectTableCssDependencies($headLink)
    {
        $css = [
            'css/datatables-1.13/buttons.dataTables.min.css',
            'css/datatables-1.13/colReorder.dataTables.min.css',
        ];
        foreach ($css as $path) {
            $headLink->appendStylesheet(Assets::url($path));
        }
    }
}
