" Author: Cole Munz https://github.com/munzzyy
" Description: output handler for noslop's --rdjson format (rdjsonl - one
" JSON object per finding, https://github.com/reviewdog/reviewdog/tree/master/proto/rdf)

function! ale#handlers#noslop#GetType(severity) abort
    if a:severity is? 'ERROR'
        return 'E'
    elseif a:severity is? 'INFO'
        return 'I'
    endif

    return 'W'
endfunction

function! ale#handlers#noslop#Handle(buffer, lines) abort
    let l:output = []

    for l:line in a:lines
        if empty(trim(l:line))
            continue
        endif

        try
            let l:finding = json_decode(l:line)
        catch
            continue
        endtry

        call add(l:output, {
        \   'lnum': l:finding.location.range.start.line,
        \   'text': l:finding.message,
        \   'type': ale#handlers#noslop#GetType(l:finding.severity),
        \})
    endfor

    return l:output
endfunction
