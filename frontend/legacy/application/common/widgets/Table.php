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
        // RASTATIME 2026-06-01 (JS-modernization stage 2): DataTables core
        // 1.9 -> 1.13 on the ?jq3 path.  The version-agnostic helper plugins
        // (pluginAPI / fnSetFilteringDelay / FixedColumns / FixedHeader /
        // columnFilter) load unchanged ($.browser/.size covered by shim +
        // migrate).  But the 2012 ColVis + ColReorder do NOT register on 1.13
        // (they silently abort the table build), so on ?jq3 they are replaced by
        // the modern Buttons (+colVis) and ColReorder 1.6 extensions; the table
        // init code (library.js / builder.js / podcast.js) branches accordingly.
        $deps = [
            'js/airtime/widgets/table.js',
            PageLayoutInitPlugin::rtDataTablesCore(),
            'js/datatables/plugin/dataTables.pluginAPI.js',
            'js/datatables/plugin/dataTables.fnSetFilteringDelay.js',
        ];
        if (PageLayoutInitPlugin::rtUseJquery3()) {
            $deps[] = 'js/datatables-1.13/extensions/dataTables.buttons.min.js';
            $deps[] = 'js/datatables-1.13/extensions/buttons.colVis.min.js';
            $deps[] = 'js/datatables-1.13/extensions/dataTables.colReorder.min.js';
        } else {
            $deps[] = 'js/datatables/plugin/dataTables.ColVis.js';
            $deps[] = 'js/datatables/plugin/dataTables.colReorder.min.js';
        }
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
}
