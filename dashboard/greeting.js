// Visitor greeting in the homepage header: "👋 Hello, visitor from Ireland 🇮🇪" + Seattle time vs theirs.
// The country comes from the browser's own time zone (no IP lookup, nothing sent anywhere); the name from
// the browser (Intl.DisplayNames) and the flag from the country code. Unknown zone -> plain Seattle greeting.
(function () {
  "use strict";
  // IANA time zone -> ISO country, from tzdata zone.tab plus legacy names browsers still report
  // (e.g. Chrome's "Asia/Calcutta"). Format: "CC:zone,zone;CC:zone..."
  const TZ_COUNTRY = "AD:Europe/Andorra;AE:Asia/Dubai;AF:Asia/Kabul;AG:America/Antigua;AI:America/Anguilla;AL:Europe/Tirane;AM:Asia/Yerevan;AO:Africa/Luanda;AQ:Antarctica/Casey,Antarctica/Davis,Antarctica/DumontDUrville,Antarctica/Mawson,Antarctica/McMurdo,Antarctica/Palmer,Antarctica/Rothera,Antarctica/Syowa,Antarctica/Troll,Antarctica/Vostok;AR:America/Argentina/Buenos_Aires,America/Argentina/Catamarca,America/Argentina/Cordoba,America/Argentina/Jujuy,America/Argentina/La_Rioja,America/Argentina/Mendoza,America/Argentina/Rio_Gallegos,America/Argentina/Salta,America/Argentina/San_Juan,America/Argentina/San_Luis,America/Argentina/Tucuman,America/Argentina/Ushuaia,America/Buenos_Aires,America/Catamarca,America/Cordoba,America/Jujuy,America/Mendoza;AS:Pacific/Pago_Pago,Pacific/Samoa;AT:Europe/Vienna;AU:Antarctica/Macquarie,Australia/ACT,Australia/Adelaide,Australia/Brisbane,Australia/Broken_Hill,Australia/Canberra,Australia/Darwin,Australia/Eucla,Australia/Hobart,Australia/Lindeman,Australia/Lord_Howe,Australia/Melbourne,Australia/NSW,Australia/Perth,Australia/Sydney;AW:America/Aruba;AX:Europe/Mariehamn;AZ:Asia/Baku;BA:Europe/Sarajevo;BB:America/Barbados;BD:Asia/Dacca,Asia/Dhaka;BE:Europe/Brussels;BF:Africa/Ouagadougou;BG:Europe/Sofia;BH:Asia/Bahrain;BI:Africa/Bujumbura;BJ:Africa/Porto-Novo;BL:America/St_Barthelemy;BM:Atlantic/Bermuda;BN:Asia/Brunei;BO:America/La_Paz;BQ:America/Kralendijk;BR:America/Araguaina,America/Bahia,America/Belem,America/Boa_Vista,America/Campo_Grande,America/Cuiaba,America/Eirunepe,America/Fortaleza,America/Maceio,America/Manaus,America/Noronha,America/Porto_Velho,America/Recife,America/Rio_Branco,America/Santarem,America/Sao_Paulo,Brazil/East;BS:America/Nassau;BT:Asia/Thimbu,Asia/Thimphu;BW:Africa/Gaborone;BY:Europe/Minsk;BZ:America/Belize;CA:America/Atikokan,America/Blanc-Sablon,America/Cambridge_Bay,America/Creston,America/Dawson,America/Dawson_Creek,America/Edmonton,America/Fort_Nelson,America/Glace_Bay,America/Goose_Bay,America/Halifax,America/Inuvik,America/Iqaluit,America/Moncton,America/Montreal,America/Rankin_Inlet,America/Regina,America/Resolute,America/St_Johns,America/Swift_Current,America/Toronto,America/Vancouver,America/Whitehorse,America/Winnipeg,Canada/Atlantic,Canada/Central,Canada/Eastern,Canada/Mountain,Canada/Pacific;CC:Indian/Cocos;CD:Africa/Kinshasa,Africa/Lubumbashi;CF:Africa/Bangui;CG:Africa/Brazzaville;CH:Europe/Zurich;CI:Africa/Abidjan;CK:Pacific/Rarotonga;CL:America/Coyhaique,America/Punta_Arenas,America/Santiago,Chile/Continental,Pacific/Easter;CM:Africa/Douala;CN:Asia/Chongqing,Asia/Harbin,Asia/Kashgar,Asia/Shanghai,Asia/Urumqi,PRC;CO:America/Bogota;CR:America/Costa_Rica;CU:America/Havana;CV:Atlantic/Cape_Verde;CW:America/Curacao;CX:Indian/Christmas;CY:Asia/Famagusta,Asia/Nicosia;CZ:Europe/Prague;DE:Europe/Berlin,Europe/Busingen;DJ:Africa/Djibouti;DK:Europe/Copenhagen;DM:America/Dominica;DO:America/Santo_Domingo;DZ:Africa/Algiers;EC:America/Guayaquil,Pacific/Galapagos;EE:Europe/Tallinn;EG:Africa/Cairo,Egypt;EH:Africa/El_Aaiun;ER:Africa/Asmara;ES:Africa/Ceuta,Atlantic/Canary,Europe/Madrid;ET:Africa/Addis_Ababa;FI:Europe/Helsinki;FJ:Pacific/Fiji;FK:Atlantic/Stanley;FM:Pacific/Chuuk,Pacific/Kosrae,Pacific/Pohnpei,Pacific/Ponape,Pacific/Truk;FO:Atlantic/Faeroe,Atlantic/Faroe;FR:Europe/Paris;GA:Africa/Libreville;GB:Europe/Belfast,Europe/London,GB;GD:America/Grenada;GE:Asia/Tbilisi;GF:America/Cayenne;GG:Europe/Guernsey;GH:Africa/Accra;GI:Europe/Gibraltar;GL:America/Danmarkshavn,America/Godthab,America/Nuuk,America/Scoresbysund,America/Thule;GM:Africa/Banjul;GN:Africa/Conakry;GP:America/Guadeloupe;GQ:Africa/Malabo;GR:Europe/Athens;GS:Atlantic/South_Georgia;GT:America/Guatemala;GU:Pacific/Guam;GW:Africa/Bissau;GY:America/Guyana;HK:Asia/Hong_Kong,Hongkong;HN:America/Tegucigalpa;HR:Europe/Zagreb;HT:America/Port-au-Prince;HU:Europe/Budapest;ID:Asia/Jakarta,Asia/Jayapura,Asia/Makassar,Asia/Pontianak,Asia/Ujung_Pandang;IE:Eire,Europe/Dublin;IL:Asia/Jerusalem,Asia/Tel_Aviv,Israel;IM:Europe/Isle_of_Man;IN:Asia/Calcutta,Asia/Kolkata;IO:Indian/Chagos;IQ:Asia/Baghdad;IR:Asia/Tehran,Iran;IS:Atlantic/Reykjavik,Iceland;IT:Europe/Rome;JE:Europe/Jersey;JM:America/Jamaica;JO:Asia/Amman;JP:Asia/Tokyo,Japan;KE:Africa/Nairobi;KG:Asia/Bishkek;KH:Asia/Phnom_Penh;KI:Pacific/Enderbury,Pacific/Kanton,Pacific/Kiritimati,Pacific/Tarawa;KM:Indian/Comoro;KN:America/St_Kitts;KP:Asia/Pyongyang;KR:Asia/Seoul,ROK;KW:Asia/Kuwait;KY:America/Cayman;KZ:Asia/Almaty,Asia/Aqtau,Asia/Aqtobe,Asia/Atyrau,Asia/Oral,Asia/Qostanay,Asia/Qyzylorda;LA:Asia/Vientiane;LB:Asia/Beirut;LC:America/St_Lucia;LI:Europe/Vaduz;LK:Asia/Colombo;LR:Africa/Monrovia;LS:Africa/Maseru;LT:Europe/Vilnius;LU:Europe/Luxembourg;LV:Europe/Riga;LY:Africa/Tripoli;MA:Africa/Casablanca;MC:Europe/Monaco;MD:Europe/Chisinau;ME:Europe/Podgorica;MF:America/Marigot;MG:Indian/Antananarivo;MH:Pacific/Kwajalein,Pacific/Majuro;MK:Europe/Skopje;ML:Africa/Bamako;MM:Asia/Rangoon,Asia/Yangon;MN:Asia/Hovd,Asia/Ulaanbaatar,Asia/Ulan_Bator;MO:Asia/Macao,Asia/Macau;MP:Pacific/Saipan;MQ:America/Martinique;MR:Africa/Nouakchott;MS:America/Montserrat;MT:Europe/Malta;MU:Indian/Mauritius;MV:Indian/Maldives;MW:Africa/Blantyre;MX:America/Bahia_Banderas,America/Cancun,America/Chihuahua,America/Ciudad_Juarez,America/Hermosillo,America/Matamoros,America/Mazatlan,America/Merida,America/Mexico_City,America/Monterrey,America/Ojinaga,America/Tijuana,Mexico/General;MY:Asia/Kuala_Lumpur,Asia/Kuching;MZ:Africa/Maputo;NA:Africa/Windhoek;NC:Pacific/Noumea;NE:Africa/Niamey;NF:Pacific/Norfolk;NG:Africa/Lagos;NI:America/Managua;NL:Europe/Amsterdam;NO:Europe/Oslo;NP:Asia/Kathmandu,Asia/Katmandu;NR:Pacific/Nauru;NU:Pacific/Niue;NZ:NZ,Pacific/Auckland,Pacific/Chatham;OM:Asia/Muscat;PA:America/Panama;PE:America/Lima;PF:Pacific/Gambier,Pacific/Marquesas,Pacific/Tahiti;PG:Pacific/Bougainville,Pacific/Port_Moresby;PH:Asia/Manila;PK:Asia/Karachi;PL:Europe/Warsaw,Poland;PM:America/Miquelon;PN:Pacific/Pitcairn;PR:America/Puerto_Rico;PS:Asia/Gaza,Asia/Hebron;PT:Atlantic/Azores,Atlantic/Madeira,Europe/Lisbon,Portugal;PW:Pacific/Palau;PY:America/Asuncion;QA:Asia/Qatar;RE:Indian/Reunion;RO:Europe/Bucharest;RS:Europe/Belgrade;RU:Asia/Anadyr,Asia/Barnaul,Asia/Chita,Asia/Irkutsk,Asia/Kamchatka,Asia/Khandyga,Asia/Krasnoyarsk,Asia/Magadan,Asia/Novokuznetsk,Asia/Novosibirsk,Asia/Omsk,Asia/Sakhalin,Asia/Srednekolymsk,Asia/Tomsk,Asia/Ust-Nera,Asia/Vladivostok,Asia/Yakutsk,Asia/Yekaterinburg,Europe/Astrakhan,Europe/Kaliningrad,Europe/Kirov,Europe/Moscow,Europe/Samara,Europe/Saratov,Europe/Ulyanovsk,Europe/Volgograd;RW:Africa/Kigali;SA:Asia/Riyadh;SB:Pacific/Guadalcanal;SC:Indian/Mahe;SD:Africa/Khartoum;SE:Europe/Stockholm;SG:Asia/Singapore,Singapore;SH:Atlantic/St_Helena;SI:Europe/Ljubljana;SJ:Arctic/Longyearbyen;SK:Europe/Bratislava;SL:Africa/Freetown;SM:Europe/San_Marino;SN:Africa/Dakar;SO:Africa/Mogadishu;SR:America/Paramaribo;SS:Africa/Juba;ST:Africa/Sao_Tome;SV:America/El_Salvador;SX:America/Lower_Princes;SY:Asia/Damascus;SZ:Africa/Mbabane;TC:America/Grand_Turk;TD:Africa/Ndjamena;TF:Indian/Kerguelen;TG:Africa/Lome;TH:Asia/Bangkok;TJ:Asia/Dushanbe;TK:Pacific/Fakaofo;TL:Asia/Dili;TM:Asia/Ashgabat;TN:Africa/Tunis;TO:Pacific/Tongatapu;TR:Europe/Istanbul,Turkey;TT:America/Port_of_Spain;TV:Pacific/Funafuti;TW:Asia/Taipei,ROC;TZ:Africa/Dar_es_Salaam;UA:Europe/Kiev,Europe/Kyiv,Europe/Simferopol,Europe/Uzhgorod,Europe/Zaporozhye;UG:Africa/Kampala;UM:Pacific/Midway,Pacific/Wake;US:America/Adak,America/Anchorage,America/Boise,America/Chicago,America/Denver,America/Detroit,America/Fort_Wayne,America/Indiana/Indianapolis,America/Indiana/Knox,America/Indiana/Marengo,America/Indiana/Petersburg,America/Indiana/Tell_City,America/Indiana/Vevay,America/Indiana/Vincennes,America/Indiana/Winamac,America/Indianapolis,America/Juneau,America/Kentucky/Louisville,America/Kentucky/Monticello,America/Knox_IN,America/Los_Angeles,America/Louisville,America/Menominee,America/Metlakatla,America/New_York,America/Nome,America/North_Dakota/Beulah,America/North_Dakota/Center,America/North_Dakota/New_Salem,America/Phoenix,America/Sitka,America/Yakutat,Pacific/Honolulu,US/Alaska,US/Arizona,US/Central,US/Eastern,US/Hawaii,US/Mountain,US/Pacific;UY:America/Montevideo;UZ:Asia/Samarkand,Asia/Tashkent;VA:Europe/Vatican;VC:America/St_Vincent;VE:America/Caracas;VG:America/Tortola;VI:America/St_Thomas;VN:Asia/Ho_Chi_Minh,Asia/Saigon;VU:Pacific/Efate;WF:Pacific/Wallis;WS:Pacific/Apia;YE:Asia/Aden;YT:Indian/Mayotte;ZA:Africa/Johannesburg;ZM:Africa/Lusaka;ZW:Africa/Harare";
  const HOME_TZ = "America/Los_Angeles";
  // Country names that read better with "the"
  const WITH_THE = new Set(["US", "GB", "NL", "PH", "AE", "DO", "BS", "GM", "MV", "MH", "SB", "KM", "CD", "CG", "CF",
                            "CZ", "VA", "KY", "FO", "FK", "TC", "VG", "VI"]);

  function countryOf(tz) {
    for (const entry of TZ_COUNTRY.split(";")) {
      const [cc, zones] = entry.split(":");
      if (zones.split(",").includes(tz)) return cc;
    }
    return null;
  }

  function flag(cc) {
    return String.fromCodePoint(...[...cc].map((c) => 0x1f1e6 + c.charCodeAt(0) - 65));
  }

  function timeIn(tz) {
    return new Intl.DateTimeFormat("en-US", { hour: "numeric", minute: "2-digit", timeZone: tz }).format(new Date());
  }

  function render(el) {
    let tz = null;
    try { tz = Intl.DateTimeFormat().resolvedOptions().timeZone; } catch (e) { /* very old browser */ }
    const cc = tz && countryOf(tz);
    let name = null;
    try { name = cc && new Intl.DisplayNames(["en"], { type: "region" }).of(cc); } catch (e) { /* no DisplayNames */ }
    const seattle = timeIn(HOME_TZ);
    const sameClock = tz && timeIn(tz) === seattle;

    const hello = el.querySelector(".vg-hello");
    const times = el.querySelector(".vg-times");
    if (cc === "US" && sameClock) {
      hello.textContent = "👋 Hello, neighbor! Greetings from Seattle";
    } else if (cc === "US") {
      hello.textContent = "👋 Hello from Seattle!";
    } else if (cc && name && name !== cc) {
      hello.textContent = `👋 Hello, visitor from ${WITH_THE.has(cc) ? "the " : ""}${name} ${flag(cc)}`;
    } else {
      hello.textContent = "👋 Hello from Seattle!";
    }
    times.textContent = sameClock || !tz
      ? `It's ${seattle} here in Seattle`
      : `It's ${seattle} here in Seattle · ${timeIn(tz)} for you`;
    el.hidden = false;
  }

  function start() {
    const el = document.getElementById("visitorGreeting");
    if (!el) return;
    render(el);
    setInterval(() => render(el), 30000);   // keep the clocks current
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
  else start();
})();
