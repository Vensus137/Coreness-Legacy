; Перед установкой удаляем папку plugins целиком, чтобы при переустановке не оставалось старых плагинов.
!macro customInit
  IfFileExists "$INSTDIR\resources\plugins" 0 +2
  RMDir /r "$INSTDIR\resources\plugins"
!macroend
