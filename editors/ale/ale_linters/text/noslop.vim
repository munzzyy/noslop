" Author: Cole Munz https://github.com/munzzyy
" Description: noslop for plain text - flags AI-sounding prose while you write

call ale#Set('text_noslop_executable', 'noslop')
call ale#Set('text_noslop_options', '')

function! ale_linters#text#noslop#GetCommand(buffer) abort
    return ale#Escape(ale#Var(a:buffer, 'text_noslop_executable'))
    \   . ' --rdjson '
    \   . ale#Var(a:buffer, 'text_noslop_options')
    \   . ' %t'
endfunction

call ale#linter#Define('text', {
\   'name': 'noslop',
\   'executable': {b -> ale#Var(b, 'text_noslop_executable')},
\   'command': function('ale_linters#text#noslop#GetCommand'),
\   'callback': 'ale#handlers#noslop#Handle',
\})
