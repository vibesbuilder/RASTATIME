<?php

/**
 * RASTATIME 2026-11-03 - Analytics -> Yearly Report (operator go 2026-11-03):
 * programme minutes of the own productions and the participants overview of
 * the archiving module on one page with one year selector.  Program
 * Managers and Admins (ACL resource 'yearlyreport').
 */
class YearlyreportController extends Zend_Controller_Action
{
    private function year(): int
    {
        $years = Application_Service_YearlyReportService::years();
        $year = (int) $this->_getParam('year', $years[0]);

        return in_array($year, $years, true) ? $year : $years[0];
    }

    public function indexAction()
    {
        Zend_Layout::getMvcInstance()->assign('parent_page', 'Analytics');
        $year = $this->year();
        $tz = new DateTimeZone(Application_Model_Preference::GetTimezone());
        $this->view->years = Application_Service_YearlyReportService::years();
        $this->view->year = $year;
        $this->view->minutes = Application_Service_YearlyReportService::minutesReport($year);
        $this->view->participants = Application_Service_ArchivingService::participantsReport($year);
        $this->view->archivingReady = Application_Service_ArchivingService::tablesReady();
        $this->view->columnReady = Application_Service_YearlyReportService::columnReady();
        $this->view->isCurrentYear = $year === (int) (new DateTime('now', $tz))->format('Y');
        $this->view->today = (new DateTime('now', $tz))->format('Y-m-d');
        $this->view->monthNames = [];
        for ($m = 1; $m <= 12; ++$m) {
            $this->view->monthNames[$m] = (new DateTime(sprintf('%04d-%02d-01', $year, $m), $tz))->format('F');
        }
    }

    /** Programme minutes of one year as CSV (UTF-8 with BOM, comma, for spreadsheets). */
    public function minutesCsvAction()
    {
        $this->view->layout()->disableLayout();
        $this->_helper->viewRenderer->setNoRender(true);
        $year = $this->year();
        $report = Application_Service_YearlyReportService::minutesReport($year);
        $out = fopen('php://temp', 'w+');
        fwrite($out, "\xEF\xBB\xBF");
        fputcsv($out, [_('Show name'), _('Own production'), _('Repeat'), _('Episodes aired'), _('Minutes')], ',', '"', '');
        foreach ($report['rows'] as $r) {
            fputcsv($out, [$r['name'], $r['own_production'] ? _('yes') : _('no'), $r['is_repeat'] ? _('yes') : '',
                $r['episodes'], $r['minutes']], ',', '"', '');
        }
        $t = $report['totals'];
        fputcsv($out, [_('Total own productions, first broadcasts'), '', '', $t['episodes_own'], $t['minutes_first']], ',', '"', '');
        fputcsv($out, [_('Total own productions, repeats'), '', '', '', $t['minutes_repeat']], ',', '"', '');
        fputcsv($out, [_('Total own productions'), '', '', $t['episodes_own'], $t['minutes_own']], ',', '"', '');
        fputcsv($out, [_('Total other shows'), '', '', $t['episodes_other'], $t['minutes_other']], ',', '"', '');
        fputcsv($out, [], ',', '"', '');
        fputcsv($out, [_('Month'), _('Episodes aired'), _('Minutes, first broadcasts'), _('Minutes, repeats')], ',', '"', '');
        $tz = new DateTimeZone(Application_Model_Preference::GetTimezone());
        foreach ($report['months'] as $m => $row) {
            fputcsv($out, [(new DateTime(sprintf('%04d-%02d-01', $year, $m), $tz))->format('F'),
                $row['episodes'], $row['minutes_first'], $row['minutes_repeat']], ',', '"', '');
        }
        rewind($out);
        $csv = stream_get_contents($out);
        fclose($out);
        $this->getResponse()
            ->setHeader('Content-Type', 'text/csv; charset=UTF-8')
            ->setHeader('Content-Disposition', 'attachment; filename="programme-minutes-' . $year . '.csv"')
            ->setBody($csv);
    }
}
