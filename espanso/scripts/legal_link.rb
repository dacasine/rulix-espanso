#!/usr/bin/env ruby
# frozen_string_literal: true

require 'open3'
require 'uri'

output, error, status = Open3.capture3(*ARGV)
abort(error.empty? ? 'Legal reference failed' : error) unless status.success?
url = output.scan(/\]\((https:\/\/[^\s)]+)\)/).last&.first
abort 'No legal URL in reference' unless url
uri = URI.parse(url)
abort 'Invalid legal URL' unless uri.scheme == 'https' && uri.host
print url
