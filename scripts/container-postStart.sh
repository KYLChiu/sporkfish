#/bin/bash

custom_prompt='export PS1="\[\e[0;36m\]\u\[\e[m\]@\[\e[0;35m\]\h\[\e[m\]:\[\e[0;33m\]\w\[\e[m\]\$ "'
if grep -qF "$custom_prompt" ~/.bashrc; then
    sed -i "s|.*export PS1.*|$custom_prompt|" ~/.bashrc
else
    echo "$custom_prompt" >> ~/.bashrc
fi

bash
clear