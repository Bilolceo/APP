"""Fayl xotirasi abstraksiyasi (FileStorage).

Bu paket provayderdan mustaqil fayl xotirasi interfeysini (`FileStorageBackend`)
va uning konkret implementatsiyalarini (`LocalFileStorage` — MVP, `S3FileStorage`
— kelajak) o'z ichiga oladi (R18.2). MVP'da faqat abstrakt interfeys
belgilanadi; konkret backendlar keyingi vazifalarda qo'shiladi.
"""
