<?php

/**
 * RASTATIME 2026-10-13 - minimal ZIP reader / writer (Section 23.52).
 *
 * The PHP build on the station has no ext-zip, and the Import/Export
 * bundle must work on a plain install, so this class implements the
 * two things the bundle needs: write a set of named entries (deflated)
 * and read all entries of an uploaded archive (stored or deflated).
 * No encryption, no ZIP64, no directories as entries - the bundle is a
 * handful of small text files plus show logos.
 */
class Application_Common_Zip
{
    /** Local file header signature. */
    const SIG_LOCAL = "PK\x03\x04";
    const SIG_CENTRAL = "PK\x01\x02";
    const SIG_EOCD = "PK\x05\x06";

    /**
     * @param array<string,string> $entries name => binary content
     *
     * @return string the archive bytes
     */
    public static function build(array $entries): string
    {
        $local = '';
        $central = '';
        $offset = 0;
        $count = 0;
        // DOS date/time: fixed to the moment of the export (local time).
        $now = time();
        $dosTime = ((int) date('H', $now) << 11) | ((int) date('i', $now) << 5) | ((int) (date('s', $now) / 2));
        $dosDate = (((int) date('Y', $now) - 1980) << 9) | ((int) date('n', $now) << 5) | (int) date('j', $now);

        foreach ($entries as $name => $content) {
            $name = str_replace('\\', '/', (string) $name);
            $content = (string) $content;
            $crc = crc32($content);
            $deflated = gzdeflate($content, 6);
            $method = 8;
            if ($deflated === false || strlen($deflated) >= strlen($content)) {
                $deflated = $content;
                $method = 0;
            }
            $nameLen = strlen($name);
            // general purpose flag bit 11 = UTF-8 names
            $header = pack('vvvvvVVVvv', 20, 0x0800, $method, $dosTime, $dosDate, $crc, strlen($deflated), strlen($content), $nameLen, 0);
            $local .= self::SIG_LOCAL . $header . $name . $deflated;
            $central .= self::SIG_CENTRAL
                . pack('vvvvvvVVVvvvvvVV', 20, 20, 0x0800, $method, $dosTime, $dosDate, $crc, strlen($deflated), strlen($content), $nameLen, 0, 0, 0, 0, 0, $offset)
                . $name;
            $offset += 30 + $nameLen + strlen($deflated);
            ++$count;
        }
        $eocd = self::SIG_EOCD . pack('vvvvVVv', 0, 0, $count, $count, strlen($central), $offset, 0);

        return $local . $central . $eocd;
    }

    public static function isZip(string $path): bool
    {
        $fh = @fopen($path, 'rb');
        if ($fh === false) {
            return false;
        }
        $sig = fread($fh, 4);
        fclose($fh);

        return $sig === self::SIG_LOCAL;
    }

    /**
     * @return array<string,string> name => content (directories skipped)
     *
     * @throws RuntimeException on a malformed or unsupported archive
     */
    public static function extract(string $path): array
    {
        $data = @file_get_contents($path);
        if ($data === false) {
            throw new RuntimeException('cannot read archive');
        }
        $eocdPos = strrpos($data, self::SIG_EOCD);
        if ($eocdPos === false) {
            throw new RuntimeException('not a ZIP archive (no end-of-central-directory record)');
        }
        $eocd = unpack('vdisk/vcddisk/ventries/vtotal/Vsize/Voffset/vcomment', substr($data, $eocdPos + 4, 18));
        $pos = $eocd['offset'];
        $out = [];
        for ($i = 0; $i < $eocd['total']; ++$i) {
            if (substr($data, $pos, 4) !== self::SIG_CENTRAL) {
                throw new RuntimeException('malformed central directory');
            }
            $h = unpack('vmade/vneed/vflag/vmethod/vtime/vdate/Vcrc/Vcsize/Vusize/vnamelen/vextralen/vcommentlen/vdisk/vattr/Vextattr/Vlocal', substr($data, $pos + 4, 42));
            $name = substr($data, $pos + 46, $h['namelen']);
            $pos += 46 + $h['namelen'] + $h['extralen'] + $h['commentlen'];
            if (substr($name, -1) === '/') {
                continue;                               // directory entry
            }
            if ($h['flag'] & 0x0001) {
                throw new RuntimeException("entry '{$name}' is encrypted");
            }
            $lp = $h['local'];
            if (substr($data, $lp, 4) !== self::SIG_LOCAL) {
                throw new RuntimeException("malformed local header for '{$name}'");
            }
            $lh = unpack('vneed/vflag/vmethod/vtime/vdate/Vcrc/Vcsize/Vusize/vnamelen/vextralen', substr($data, $lp + 4, 26));
            $start = $lp + 30 + $lh['namelen'] + $lh['extralen'];
            $raw = substr($data, $start, $h['csize']);
            if ($h['method'] === 0) {
                $content = $raw;
            } elseif ($h['method'] === 8) {
                $content = @gzinflate($raw);
                if ($content === false) {
                    throw new RuntimeException("cannot inflate '{$name}'");
                }
            } else {
                throw new RuntimeException("entry '{$name}' uses an unsupported compression method");
            }
            if (strlen($content) !== $h['usize'] || crc32($content) !== $h['crc']) {
                throw new RuntimeException("entry '{$name}' is corrupt (size or CRC mismatch)");
            }
            $out[str_replace('\\', '/', $name)] = $content;
        }

        return $out;
    }
}
