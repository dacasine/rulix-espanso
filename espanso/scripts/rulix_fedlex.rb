#!/usr/bin/env ruby
# frozen_string_literal: true

require 'csv'

EMBEDDED_DATA = DATA.read

LANG_CONFIG = {
  'fr' => { rs: 'RS', art: 'art.', para: 'al.', letter: 'let.', number: 'ch.', cite: 'ci-après' },
  'de' => { rs: 'SR', art: 'Art.', para: 'Abs.', letter: 'Bst.', number: 'Ziff.', cite: 'nachfolgend' },
  'it' => { rs: 'RS', art: 'art.', para: 'cpv.', letter: 'lett.', number: 'n.', cite: 'di seguito' }
}.freeze

ROMAN = {
  'i' => 1, 'ii' => 2, 'iii' => 3, 'iv' => 4, 'v' => 5,
  'vi' => 6, 'vii' => 7, 'viii' => 8, 'ix' => 9, 'x' => 10
}.freeze

Law = Struct.new(:key, :abbr_fr, :abbr_de, :abbr_it, :rs, :title_fr, :title_de, :title_it, :url_override, keyword_init: true) do
  def abbr(lang)
    public_send("abbr_#{lang}") || abbr_fr
  end

  def title(lang)
    public_send("title_#{lang}") || title_fr
  end

  def url(lang)
    if url_override && !url_override.empty?
      return url_override.sub(%r{/fr(?=$|[#?])}, "/#{lang}")
    end

    "https://www.fedlex.admin.ch/#{lang}/cc/internal-law/#{rs}"
  end

  def normalized_keys
    [key, abbr_fr, abbr_de, abbr_it].compact.map do |value|
      value.downcase.gsub(/[^a-z0-9]/, '')
    end.uniq
  end
end

def laws
  @laws ||= CSV.parse(EMBEDDED_DATA, headers: true, col_sep: '|').map do |row|
    Law.new(
      key: row['key'],
      abbr_fr: row['abbr_fr'],
      abbr_de: row['abbr_de'],
      abbr_it: row['abbr_it'],
      rs: row['rs'],
      title_fr: row['title_fr'],
      title_de: row['title_de'],
      title_it: row['title_it'],
      url_override: row['url_override']
    )
  end
end

def law_for(input)
  needle = input.to_s.downcase.gsub(/[^a-z0-9]/, '')
  laws.find { |law| law.normalized_keys.include?(needle) }
end

def citation(law, lang)
  cfg = LANG_CONFIG.fetch(lang)
  "#{law.title(lang)} (#{cfg[:cite]} #{law.abbr(lang)}, [#{cfg[:rs]} #{law.rs}](#{law.url(lang)}))"
end

def labels(lang)
  cfg = LANG_CONFIG.fetch(lang)
  laws.map { |law| "#{law.key}|#{law.abbr(lang)} - #{law.title(lang)} - #{cfg[:rs]} #{law.rs}" }.join("\n")
end

def parse_reference(raw)
  match = raw.to_s.match(/\A(?<digits>\d+)(?<rest>[a-z0-9]*)\z/i)
  return nil unless match

  article = match[:digits]
  rest = match[:rest].downcase
  para = nil
  letter = nil
  number = nil

  unless rest.empty?
    roman_at_start = ROMAN.keys.sort_by { |r| -r.length }.find { |r| rest.start_with?(r) }
    unless roman_at_start
      article += rest[0]
      rest = rest[1..] || ''
    end
  end

  unless rest.empty?
    roman = ROMAN.keys.sort_by { |r| -r.length }.find { |r| rest.start_with?(r) }
    if roman
      para = ROMAN.fetch(roman)
      rest = rest[roman.length..] || ''
    end
  end

  if rest.match?(/\A[a-z]/)
    letter = rest[0]
    rest = rest[1..] || ''
  end

  number = rest if rest.match?(/\A\d+\z/)
  { article: article, para: para, letter: letter, number: number }
end

def article_reference(law, lang, raw_ref)
  cfg = LANG_CONFIG.fetch(lang)
  parsed = parse_reference(raw_ref)
  abort "Référence invalide: #{raw_ref}" unless parsed

  text = "#{cfg[:art]} #{parsed[:article]}"
  text += " #{cfg[:para]} #{parsed[:para]}" if parsed[:para]
  text += " #{cfg[:letter]} #{parsed[:letter]}" if parsed[:letter]
  text += " #{cfg[:number]} #{parsed[:number]}" if parsed[:number]
  text += " #{law.abbr(lang)}"

  "[#{text}](#{law.url(lang)}#art_#{parsed[:article]})"
end

mode, lang, *args = ARGV
lang ||= 'fr'
abort "Langue inconnue: #{lang}" unless LANG_CONFIG.key?(lang)

case mode
when 'labels'
  puts labels(lang)
when 'citation'
  selected = args.join(' ')
  key = selected.split('|', 2).first
  law = law_for(key)
  abort "Loi inconnue: #{selected}" unless law
  puts citation(law, lang)
when 'article'
  law = law_for(args[0])
  abort "Loi inconnue: #{args[0]}" unless law
  puts article_reference(law, lang, args[1])
when 'keys'
  puts laws.flat_map(&:normalized_keys).uniq.sort_by { |key| [-key.length, key] }.join('|')
else
  abort "Usage: rulix_fedlex.rb labels|citation|article|keys [lang] [...]"
end

__END__
key|abbr_fr|abbr_de|abbr_it|rs|title_fr|title_de|title_it|url_override
cst|Cst.|BV|Cost.|101|Constitution fédérale de la Confédération suisse|Bundesverfassung der Schweizerischen Eidgenossenschaft|Costituzione federale della Confederazione Svizzera|
cc|CC|ZGB|CC|210|Code civil suisse|Schweizerisches Zivilgesetzbuch|Codice civile svizzero|https://www.fedlex.admin.ch/eli/cc/24/233_245_233/fr
co|CO|OR|CO|220|Code des obligations|Obligationenrecht|Codice delle obbligazioni|https://www.fedlex.admin.ch/eli/cc/27/317_321_377/fr
cpc|CPC|ZPO|CPC|272|Code de procédure civile suisse|Schweizerische Zivilprozessordnung|Codice di diritto processuale civile svizzero|
cp|CP|StGB|CP|311.0|Code pénal suisse|Schweizerisches Strafgesetzbuch|Codice penale svizzero|
cpp|CPP|StPO|CPP|312.0|Code de procédure pénale suisse|Schweizerische Strafprozessordnung|Codice di diritto processuale penale svizzero|
lpa|LPA|VwVG|PA|172.021|Loi fédérale sur la procédure administrative|Bundesgesetz über das Verwaltungsverfahren|Legge federale sulla procedura amministrativa|
ltf|LTF|BGG|LTF|173.110|Loi sur le Tribunal fédéral|Bundesgerichtsgesetz|Legge sul Tribunale federale|
taf|LTAF|VGG|LTAF|173.32|Loi sur le Tribunal administratif fédéral|Verwaltungsgerichtsgesetz|Legge sul Tribunale amministrativo federale|
loap|LOAP|StBOG|LOAP|173.71|Loi sur l'organisation des autorités pénales|Bundesgesetz über die Organisation der Strafbehörden des Bundes|Legge sull'organizzazione delle autorità penali|
lpd|LPD|DSG|LPD|235.1|Loi fédérale sur la protection des données|Bundesgesetz über den Datenschutz|Legge federale sulla protezione dei dati|
lcd|LCD|UWG|LCSl|241|Loi fédérale contre la concurrence déloyale|Bundesgesetz gegen den unlauteren Wettbewerb|Legge federale contro la concorrenza sleale|
ldip|LDIP|IPRG|LDIP|291|Loi fédérale sur le droit international privé|Bundesgesetz über das Internationale Privatrecht|Legge federale sul diritto internazionale privato|
letr|LEI|AIG|LStrI|142.20|Loi fédérale sur les étrangers et l'intégration|Bundesgesetz über die Ausländerinnen und Ausländer und über die Integration|Legge federale sugli stranieri e la loro integrazione|
lasi|LAsi|AsylG|LAsi|142.31|Loi sur l'asile|Asylgesetz|Legge sull'asilo|
lavi|LAVI|OHG|LAV|312.5|Loi fédérale sur l'aide aux victimes d'infractions|Bundesgesetz über die Hilfe an Opfer von Straftaten|Legge federale concernente l'aiuto alle vittime di reati|
larm|LArm|WG|LArm|514.54|Loi fédérale sur les armes, les accessoires d'armes et les munitions|Waffengesetz|Legge federale sulle armi, gli accessori di armi e le munizioni|
lcart|LCart|KG|LCart|251|Loi fédérale sur les cartels et autres restrictions à la concurrence|Bundesgesetz über Kartelle und andere Wettbewerbsbeschränkungen|Legge federale sui cartelli e altre limitazioni della concorrenza|
lp|LP|SchKG|LEF|281.1|Loi fédérale sur la poursuite pour dettes et la faillite|Bundesgesetz über Schuldbetreibung und Konkurs|Legge federale sulla esecuzione e sul fallimento|
lfaie|LFAIE|BewG|LAFE|211.412.41|Loi fédérale sur l'acquisition d'immeubles par des personnes à l'étranger|Bundesgesetz über den Erwerb von Grundstücken durch Personen im Ausland|Legge federale sull'acquisto di fondi da parte di persone all'estero|
lpart|LPart|PartG|LUD|211.231|Loi fédérale sur le partenariat enregistré entre personnes du même sexe|Bundesgesetz über die eingetragene Partnerschaft gleichgeschlechtlicher Paare|Legge federale sull'unione domestica registrata di coppie omosessuali|
loe|ORFI|VZG|RFF|281.42|Ordonnance du Tribunal fédéral sur la réalisation forcée des immeubles|Verordnung des Bundesgerichts über die Zwangsverwertung von Grundstücken|Regolamento del Tribunale federale concernente la realizzazione forzata di fondi|
oelp|OELP|GebV SchKG|OTLEF|281.35|Ordonnance sur les émoluments perçus en application de la LP|Gebührenverordnung zum Bundesgesetz über Schuldbetreibung und Konkurs|Ordinanza sulle tasse riscosse in applicazione della LEF|
obi|OBI|PatV|OBI|232.141|Ordonnance sur les brevets d'invention|Patentverordnung|Ordinanza sui brevetti|
lpdif|LTrans|BGÖ|LTras|152.3|Loi fédérale sur le principe de la transparence dans l'administration|Bundesgesetz über das Öffentlichkeitsprinzip der Verwaltung|Legge federale sul principio di trasparenza dell'amministrazione|
lpp|LPP|BVG|LPP|831.40|Loi fédérale sur la prévoyance professionnelle vieillesse, survivants et invalidité|Bundesgesetz über die berufliche Alters-, Hinterlassenen- und Invalidenvorsorge|Legge federale sulla previdenza professionale per la vecchiaia, i superstiti e l'invalidità|
opp2|OPP 2|BVV 2|OPP 2|831.441.1|Ordonnance sur la prévoyance professionnelle vieillesse, survivants et invalidité|Verordnung über die berufliche Alters-, Hinterlassenen- und Invalidenvorsorge|Ordinanza sulla previdenza professionale per la vecchiaia, i superstiti e l'invalidità|
olp|OLP|FZV|OLP|831.425|Ordonnance sur le libre passage dans la prévoyance professionnelle vieillesse, survivants et invalidité|Freizügigkeitsverordnung|Ordinanza sul libero passaggio nella previdenza professionale per la vecchiaia, i superstiti e l'invalidità|
lflp|LFLP|FZG|LFLP|831.42|Loi fédérale sur le libre passage dans la prévoyance professionnelle vieillesse, survivants et invalidité|Freizügigkeitsgesetz|Legge federale sul libero passaggio nella previdenza professionale per la vecchiaia, i superstiti e l'invalidità|
lamal|LAMal|KVG|LAMal|832.10|Loi fédérale sur l'assurance-maladie|Bundesgesetz über die Krankenversicherung|Legge federale sull'assicurazione malattie|
lca|LCA|VVG|LCA|221.229.1|Loi fédérale sur le contrat d'assurance|Bundesgesetz über den Versicherungsvertrag|Legge federale sul contratto d'assicurazione|
lpaa|LPGA|ATSG|LPGA|830.1|Loi fédérale sur la partie générale du droit des assurances sociales|Bundesgesetz über den Allgemeinen Teil des Sozialversicherungsrechts|Legge federale sulla parte generale del diritto delle assicurazioni sociali|
lavs|LAVS|AHVG|LAVS|831.10|Loi fédérale sur l'assurance-vieillesse et survivants|Bundesgesetz über die Alters- und Hinterlassenenversicherung|Legge federale sull'assicurazione per la vecchiaia e per i superstiti|
lai|LAI|IVG|LAI|831.20|Loi fédérale sur l'assurance-invalidité|Bundesgesetz über die Invalidenversicherung|Legge federale sull'assicurazione per l'invalidità|
lpc|LPC|ELG|LPC|831.30|Loi fédérale sur les prestations complémentaires à l'AVS et à l'AI|Bundesgesetz über Ergänzungsleistungen zur Alters-, Hinterlassenen- und Invalidenversicherung|Legge federale sulle prestazioni complementari all'assicurazione per la vecchiaia, i superstiti e l'invalidità|
lpers|LPers|BPG|LPers|172.220.1|Loi sur le personnel de la Confédération|Bundespersonalgesetz|Legge sul personale federale|
lcr|LCR|SVG|LCStr|741.01|Loi fédérale sur la circulation routière|Strassenverkehrsgesetz|Legge federale sulla circolazione stradale|
ocr|OCR|VRV|ONC|741.11|Ordonnance sur les règles de la circulation routière|Verkehrsregelnverordnung|Ordinanza sulle norme della circolazione stradale|
oac|OAC|VZV|OAC|741.51|Ordonnance réglant l'admission des personnes et des véhicules à la circulation routière|Verkehrszulassungsverordnung|Ordinanza sull'ammissione alla circolazione di persone e veicoli|
lifd|LIFD|DBG|LIFD|642.11|Loi fédérale sur l'impôt fédéral direct|Bundesgesetz über die direkte Bundessteuer|Legge federale sull'imposta federale diretta|
lhid|LHID|StHG|LAID|642.14|Loi fédérale sur l'harmonisation des impôts directs des cantons et des communes|Bundesgesetz über die Harmonisierung der direkten Steuern der Kantone und Gemeinden|Legge federale sull'armonizzazione delle imposte dirette dei Cantoni e dei Comuni|
ltva|LTVA|MWSTG|LIVA|641.20|Loi fédérale régissant la taxe sur la valeur ajoutée|Mehrwertsteuergesetz|Legge federale concernente l'imposta sul valore aggiunto|
co2|CO2|CO2|CO2|641.71|Loi fédérale sur la réduction des émissions de CO2|Bundesgesetz über die Reduktion der CO2-Emissionen|Legge federale sulla riduzione delle emissioni di CO2|
leaux|LEaux|GSchG|LPAc|814.20|Loi fédérale sur la protection des eaux|Gewässerschutzgesetz|Legge federale sulla protezione delle acque|
lpe|LPE|USG|LPAmb|814.01|Loi fédérale sur la protection de l'environnement|Umweltschutzgesetz|Legge federale sulla protezione dell'ambiente|
lat|LAT|RPG|LPT|700|Loi fédérale sur l'aménagement du territoire|Raumplanungsgesetz|Legge federale sulla pianificazione del territorio|
lfo|LFo|WaG|LFo|921.0|Loi fédérale sur les forêts|Waldgesetz|Legge federale sulle foreste|
lchp|LChP|JSG|LCP|922.0|Loi fédérale sur la chasse et la protection des mammifères et oiseaux sauvages|Jagdgesetz|Legge federale sulla caccia e la protezione dei mammiferi e degli uccelli selvatici|
lpn|LPN|NHG|LPN|451|Loi fédérale sur la protection de la nature et du paysage|Bundesgesetz über den Natur- und Heimatschutz|Legge federale sulla protezione della natura e del paesaggio|
laam|LAAM|MG|LM|510.10|Loi fédérale sur l'armée et l'administration militaire|Militärgesetz|Legge federale sull'esercito e sull'amministrazione militare|
lmp|LMP|BöB|LAPub|172.056.1|Loi fédérale sur les marchés publics|Bundesgesetz über das öffentliche Beschaffungswesen|Legge federale sugli appalti pubblici|
lsa|LSA|VAG|LSA|961.01|Loi sur la surveillance des assurances|Versicherungsaufsichtsgesetz|Legge sulla sorveglianza degli assicuratori|
lhand|LHand|BehiG|LDis|151.3|Loi fédérale sur l'élimination des inégalités frappant les personnes handicapées|Behindertengleichstellungsgesetz|Legge sui disabili|
cedh|CEDH|EMRK|CEDU|0.101|Convention de sauvegarde des droits de l'homme et des libertés fondamentales|Konvention zum Schutze der Menschenrechte und Grundfreiheiten|Convenzione per la salvaguardia dei diritti dell'uomo e delle libertà fondamentali|
onu2|Pacte ONU II|UNO-Pakt II|Patto ONU II|0.103.2|Pacte international relatif aux droits civils et politiques|Internationaler Pakt über bürgerliche und politische Rechte|Patto internazionale relativo ai diritti civili e politici|
onu1|Pacte ONU I|UNO-Pakt I|Patto ONU I|0.103.1|Pacte international relatif aux droits économiques, sociaux et culturels|Internationaler Pakt über wirtschaftliche, soziale und kulturelle Rechte|Patto internazionale relativo ai diritti economici, sociali e culturali|
cvdt|CVDT|WVRK|CVDT|0.111|Convention de Vienne sur le droit des traités|Wiener Übereinkommen über das Recht der Verträge|Convenzione di Vienna sul diritto dei trattati|
cvrc|CVRC|WÜK|CVRC|0.191.02|Convention de Vienne sur les relations consulaires|Wiener Übereinkommen über konsularische Beziehungen|Convenzione di Vienna sulle relazioni consolari|
istanbul|Convention d'Istanbul|Istanbul-Konvention|Convenzione di Istanbul|0.311.35|Convention du Conseil de l'Europe sur la prévention et la lutte contre la violence à l'égard des femmes et la violence domestique|Übereinkommen des Europarats zur Verhütung und Bekämpfung von Gewalt gegen Frauen und häuslicher Gewalt|Convenzione del Consiglio d'Europa sulla prevenzione e la lotta contro la violenza nei confronti delle donne e la violenza domestica|
clah80|CLaH 1980|HKÜ 1980|CLaA 1980|0.211.230.02|Convention de La Haye sur les aspects civils de l'enlèvement international d'enfants|Haager Übereinkommen über die zivilrechtlichen Aspekte internationaler Kindesentführung|Convenzione dell'Aia sugli aspetti civili del rapimento internazionale di minori|
clah96|CLaH 1996|HKsÜ 1996|CLaA 1996|0.211.231.011|Convention de La Haye concernant la compétence, la loi applicable, la reconnaissance, l'exécution et la coopération en matière de responsabilité parentale et de mesures de protection des enfants|Haager Kindesschutzübereinkommen|Convenzione dell'Aia sulla protezione dei minori|
clahadult|CLaH protection adultes|HEsÜ Erwachsenenschutz|CLaA protezione adulti|0.211.232.1|Convention de La Haye sur la protection internationale des adultes|Haager Erwachsenenschutzübereinkommen|Convenzione dell'Aia sulla protezione internazionale degli adulti|
clahalim|CLaH aliments|HUÜ Unterhalt|CLaA alimenti|0.211.213.02|Convention de La Haye sur le recouvrement international des aliments destinés aux enfants et à d'autres membres de la famille|Haager Unterhaltsübereinkommen|Convenzione dell'Aia sull'esazione internazionale di prestazioni alimentari nei confronti di figli e altri membri della famiglia|
clahproc|CLaH procédure civile|HZPÜ|CLaA procedura civile|0.274.12|Convention de La Haye relative à la procédure civile|Haager Übereinkommen betreffend Zivilprozessrecht|Convenzione dell'Aia relativa alla procedura civile|
clahapostille|CLaH apostille|Apostille-Übereinkommen|CLaA apostille|0.172.030.4|Convention de La Haye supprimant l'exigence de la légalisation des actes publics étrangers|Haager Apostille-Übereinkommen|Convenzione dell'Aia che sopprime la legalizzazione degli atti pubblici esteri|
clug|CL|LugÜ|CLug|0.275.12|Convention de Lugano concernant la compétence judiciaire, la reconnaissance et l'exécution des décisions en matière civile et commerciale|Lugano-Übereinkommen|Convenzione di Lugano|
