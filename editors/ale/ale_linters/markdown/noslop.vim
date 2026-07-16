" Author: Cole Munz https://github.com/munzzyy
" Description: noslop for Markdown - flags AI-sounding prose while you write

call ale#Set('markdown_noslop_executable', 'noslop')
call ale#Set('markdown_noslop_options', '')

function! ale_linters#markdown#noslop#GetCommand(buffer) abort
    return ale#Escape(ale#Var(a:buffer, 'markdown_noslop_executable'))
    \   . ' --rdjson '
    \   . ale#Var(a:buffer, 'markdown_noslop_options')
    \   . ' %t'
endfunction

call ale#linter#Define('markdown', {
\   'name': 'noslop',
\   'executable': {b -> ale#Var(b, 'markdown_noslop_executable')},
\   'command': function('ale_linters#markdown#noslop#GetCommand'),
\   'callback': 'ale#handlers#noslop#Handle',
\})
