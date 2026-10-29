require 'yaml'
require 'open3'

root = ARGV.fetch(0)
matches = Dir[File.join(root, 'espanso/match/*.yml')].flat_map do |path|
  rows = YAML.load_file(path).fetch('matches', [])
  rows.each do |m|
    abort "Trigger without space in #{path}: #{m['trigger']}" if m['trigger'] && !m['trigger'].end_with?(' ')
    abort "Regex without space in #{path}" if m['regex'] && !m['regex'].end_with?(' ')
  end
  # One workstation installs one language profile; audit delimiters in every file.
  inactive = File.basename(path).start_with?('_') || path.match?(/-(?:de|it)(?:-links)?\.yml\z/)
  inactive ? [] : rows
end

def expand(matches, typed, root)
  match = matches.find { |m| m['trigger'] == typed }
  captures = {}
  unless match
    matches.select { |m| m['regex'] }.each do |m|
      found = Regexp.new('\\A' + m['regex'].gsub('(?P<', '(?<') + '\\z').match(typed)
      next unless found
      match = m
      captures = found.named_captures
      break
    end
  end
  abort "No match: #{typed}" unless match
  rendered = match.fetch('replace')
  match.fetch('vars', []).each do |var|
    next unless var['type'] == 'shell'
    cmd = var['params']['cmd'].gsub('$HOME/Library/Application Support/espanso', File.join(root, 'espanso'))
    captures.each { |name, value| cmd = cmd.gsub("{{#{name}}}", value) }
    output, error, status = Open3.capture3(cmd)
    abort "Command failed for #{typed}: #{error}" unless status.success?
    rendered = rendered.gsub("{{#{var['name']}}}", output.strip)
  end
  abort "Missing newline: #{typed}" unless rendered.end_with?("\n")
  abort "Malformed URL: #{rendered.inspect}" unless rendered.match?(%r{\Ahttps://[^\s)]+\n\z})
  puts "#{typed.inspect} => #{rendered.inspect}"
  rendered
end

if File.exist?(File.join(root, 'espanso/match/base.yml'))
  url = expand(matches, 'lcc1i ', root)
  abort 'Wrong CC anchor' unless url.end_with?("#art_1\n")
  expand(matches, 'lcc176ib ', root)
  expand(matches, 'lrscc ', root)
  expand(matches, 'lrsvdlatc ', root)
  expand(matches, 'lvslacc1i ', root)
else
  expand(matches, 'lrscc ', root)
  expand(matches, 'lvslacc1i ', root)
end

%w[lcc1i lrscc lrsvdlatc bcm bcmm].each do |unfinished|
  matches.each do |m|
    abort "Early expansion: #{unfinished}" if m['trigger'] && unfinished.end_with?(m['trigger'])
    next unless m['regex']
    abort "Early regex: #{unfinished}" if Regexp.new(m['regex'].gsub('(?P<', '(?<')).match?(unfinished)
  end
end

# Espanso searches for suffix matches, not only whole-string matches.
# Normal article rules must not also match inside l-prefixed or cantonal ones.
legal_regexes = matches.select { |m| m['regex'] && m['regex'].match?(/fedlex_law|rulix_law/) }
%w[lcc1i cc1i lvslacc1i vslacc1i].each do |shortcut|
  ['', ' '].each do |prefix|
    input = prefix + shortcut + ' '
    hits = legal_regexes.select { |m| Regexp.new(m['regex'].gsub('(?P<', '(?<')).match?(input) }
    abort "Overlapping article rules for #{input.inspect}: #{hits.length}" unless hits.length == 1
  end
  input = 'x' + shortcut + ' '
  abort "Article inside a word: #{input}" if legal_regexes.any? { |m| Regexp.new(m['regex'].gsub('(?P<', '(?<')).match?(input) }
end
puts 'Article boundaries OK: one candidate at start/after space, none inside words'
puts "All #{matches.size} matches wait for a space; link examples OK"
