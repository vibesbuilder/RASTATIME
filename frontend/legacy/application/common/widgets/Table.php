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
        return [
            'js/airtime/widgets/table.js',
            // RASTATIME 2026-06-01 (JS-modernization stage 2): DataTables core
            // 1.9 -> 1.13 on the ?jq3 path (1.13 keeps the legacy plugin API, so
            // the 1.9 ColVis/columnFilter/colReorder/Fixed* plugins below load
            // unchanged; their $.browser/.size usage is covered by the shim +
            // migrate).
            PageLayoutInitPlugin::rtDataTablesCore(),
            'js/datatables/plugin/dataTables.pluginAPI.js',
            'js/datatables/plugin/dataTables.fnSetFilteringDelay.js',
            'js/datatables/plugin/dataTables.ColVis.js',
            'js/datatables/plugin/dataTables.colReorder.min.js',
            'js/datatables/plugin/dataTables.FixedColumns.js',
            'js/datatables/plugin/dataTables.FixedHeader.js',
            'js/datatables/plugin/dataTables.columnFilter.js',
        ];
    }

    public static function injectTableJavaScriptDependencies(&$headScript)
    {
        foreach (self::_getTableJavaScriptDependencies() as $path) {
            $headScript->appendFile(Assets::url($path), 'text/javascript');
        }
    }
}
