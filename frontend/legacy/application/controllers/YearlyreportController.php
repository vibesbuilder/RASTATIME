<?php

/**
 * RASTATIME 2026-11-03 - Analytics -> Programme Minutes (operator go
 * 2026-11-03): the minutes of the own productions per year.  Until
 * 2026-11-04 the "Yearly Report" with the participants overview, which is
 * its own menu entry now (Analytics -> People Involved, archiving/
 * participants).  Program Managers and Admins (ACL resource 'yearlyreport').
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
        $this->view->columnReady = Application_Service_YearlyReportService::columnReady();
        $this->view->isCurrentYear = $year === (int) (new DateTime('now', $tz))->format('Y');
        $this->view->today = (new DateTime('now', $tz))->format('Y-m-d');
        $this->view->monthNames = [];
        for ($m = 1; $m <= 12; ++$m) {
            $this->view->monthNames[$m] = (new DateTime(sprintf('%04d-%02d-01', $year, $m), $tz))->format('F');
        }
    }

    /** RASTATIME 2026-11-08 - the year of Music by Country (years with playout history). */
    private function countryYear(): int
    {
        $years = Application_Service_MusicCountryReportService::years();
        $year = (int) $this->_getParam('year', $years[0]);

        return in_array($year, $years, true) ? $year : $years[0];
    }

    /** @return array<int, string> month number => name in the station's locale */
    private function monthNames(int $year): array
    {
        $tz = new DateTimeZone(Application_Model_Preference::GetTimezone());
        $names = [];
        for ($m = 1; $m <= 12; ++$m) {
            $names[$m] = (new DateTime(sprintf('%04d-%02d-01', $year, $m), $tz))->format('F');
        }

        return $names;
    }

    /**
     * RASTATIME 2026-11-08 - Analytics -> Music by Country (operator go
     * 2026-11-08): plays and minutes of the music per country of one year.
     */
    public function countryAction()
    {
        Zend_Layout::getMvcInstance()->assign('parent_page', 'Analytics');
        $year = $this->countryYear();
        $tz = new DateTimeZone(Application_Model_Preference::GetTimezone());
        $this->view->years = Application_Service_MusicCountryReportService::years();
        $this->view->year = $year;
        $this->view->report = Application_Service_MusicCountryReportService::report($year);
        $this->view->isCurrentYear = $year === (int) (new DateTime('now', $tz))->format('Y');
        $this->view->today = (new DateTime('now', $tz))->format('Y-m-d');
        $this->view->monthNames = $this->monthNames($year);
    }

    /** Music by country of one year as CSV (UTF-8 with BOM, comma, for spreadsheets). */
    public function countryCsvAction()
    {
        $this->view->layout()->disableLayout();
        $this->_helper->viewRenderer->setNoRender(true);
        $year = $this->countryYear();
        $report = Application_Service_MusicCountryReportService::report($year);
        $months = $this->monthNames($year);
        $noCountry = _('No country');
        $pct = static fn ($v) => number_format((float) $v, 1, '.', '');
        $out = fopen('php://temp', 'w+');
        fwrite($out, "\xEF\xBB\xBF");
        fputcsv($out, [_('Country'), _('Plays'), _('Share of plays (%)'), _('Minutes'), _('Share of minutes (%)')], ',', '"', '');
        foreach ($report['rows'] as $r) {
            fputcsv($out, [$r['country'] ?? $noCountry, $r['plays'], $pct($r['share_plays']), $r['minutes'], $pct($r['share_minutes'])], ',', '"', '');
        }
        $t = $report['totals'];
        fputcsv($out, [_('Total'), $t['plays'], '100.0', $t['minutes'], '100.0'], ',', '"', '');
        fputcsv($out, [], ',', '"', '');
        fputcsv($out, [_('Month'), _('Plays'), _('Minutes'), _('Minutes with a country'), _('Share with a country (%)')], ',', '"', '');
        foreach ($report['months'] as $m => $row) {
            fputcsv($out, [$months[$m], $row['plays'], $row['minutes'], $row['minutes_tagged'], $pct($row['share_tagged'])], ',', '"', '');
        }
        fputcsv($out, [], ',', '"', '');
        fputcsv($out, array_merge([_('Minutes per month')], array_values($months), [_('Total')]), ',', '"', '');
        foreach ($report['matrix'] as $country => $cells) {
            fputcsv($out, array_merge([$country === '' ? $noCountry : $country], array_values($cells), [array_sum($cells)]), ',', '"', '');
        }
        rewind($out);
        $csv = stream_get_contents($out);
        fclose($out);
        $this->getResponse()
            ->setHeader('Content-Type', 'text/csv; charset=UTF-8')
            ->setHeader('Content-Disposition', 'attachment; filename="music-by-country-' . $year . '.csv"')
            ->setBody($csv);
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
